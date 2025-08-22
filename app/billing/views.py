import os
import stripe
from django.conf import settings
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import View
import json
import logging
from datetime import datetime

from core.models import Tenant, Plan, Subscription, BillingEvent
from .serializers import PlanSerializer, SubscriptionSerializer

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing subscription plans.
    """
    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated]


class BillingViewSet(viewsets.ViewSet):
    """
    ViewSet for billing operations including subscription management.
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def current_subscription(self, request):
        """Get current tenant's subscription details."""
        try:
            tenant = Tenant.objects.get(schema_name=request.tenant.schema_name)
            subscription = getattr(tenant, 'subscription', None)
            
            if subscription:
                serializer = SubscriptionSerializer(subscription)
                return Response(serializer.data)
            else:
                # Create free subscription if none exists
                free_plan = Plan.objects.get(slug='free')
                subscription = Subscription.objects.create(
                    tenant=tenant,
                    plan=free_plan,
                    status='active'
                )
                serializer = SubscriptionSerializer(subscription)
                return Response(serializer.data)
                
        except Exception as e:
            logger.error(f"Error fetching subscription: {str(e)}")
            return Response(
                {'error': 'Failed to fetch subscription'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def create_checkout_session(self, request):
        """Create Stripe checkout session for subscription upgrade."""
        try:
            plan_slug = request.data.get('plan')
            if not plan_slug:
                return Response(
                    {'error': 'Plan is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            plan = Plan.objects.get(slug=plan_slug, is_active=True)
            if not plan.stripe_price_id:
                return Response(
                    {'error': 'Plan not available for purchase'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            tenant = Tenant.objects.get(schema_name=request.tenant.schema_name)
            
            # Create or get Stripe customer
            if not tenant.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=request.user.email,
                    name=tenant.name,
                    metadata={'tenant_id': tenant.id}
                )
                tenant.stripe_customer_id = customer.id
                tenant.save()
            
            # Create checkout session
            session = stripe.checkout.Session.create(
                customer=tenant.stripe_customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': plan.stripe_price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=f"{settings.SITE_DOMAIN}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{settings.SITE_DOMAIN}/billing/cancel",
                metadata={
                    'tenant_id': tenant.id,
                    'plan_id': plan.id
                }
            )
            
            return Response({
                'checkout_url': session.url,
                'session_id': session.id
            })
            
        except Plan.DoesNotExist:
            return Response(
                {'error': 'Plan not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error creating checkout session: {str(e)}")
            return Response(
                {'error': 'Failed to create checkout session'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def cancel_subscription(self, request):
        """Cancel current subscription."""
        try:
            tenant = Tenant.objects.get(schema_name=request.tenant.schema_name)
            subscription = getattr(tenant, 'subscription', None)
            
            if not subscription or not subscription.stripe_subscription_id:
                return Response(
                    {'error': 'No active subscription found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Cancel subscription in Stripe
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )
            
            return Response({'message': 'Subscription will be canceled at the end of the current period'})
            
        except Exception as e:
            logger.error(f"Error canceling subscription: {str(e)}")
            return Response(
                {'error': 'Failed to cancel subscription'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def billing_portal(self, request):
        """Create Stripe billing portal session."""
        try:
            tenant = Tenant.objects.get(schema_name=request.tenant.schema_name)
            
            if not tenant.stripe_customer_id:
                return Response(
                    {'error': 'No billing information found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Create billing portal session
            session = stripe.billing_portal.Session.create(
                customer=tenant.stripe_customer_id,
                return_url=f"{settings.SITE_DOMAIN}/billing/"
            )
            
            return Response({'portal_url': session.url})
            
        except Exception as e:
            logger.error(f"Error creating billing portal: {str(e)}")
            return Response(
                {'error': 'Failed to create billing portal'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    """
    Handle Stripe webhook events.
    """
    
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError:
            logger.error("Invalid payload in webhook")
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid signature in webhook")
            return HttpResponse(status=400)
        
        # Log the event
        billing_event = BillingEvent.objects.create(
            stripe_event_id=event['id'],
            event_type=event['type'],
            data=event['data']
        )
        
        try:
            if event['type'] == 'checkout.session.completed':
                self._handle_checkout_completed(event['data']['object'])
            
            elif event['type'] == 'customer.subscription.created':
                self._handle_subscription_created(event['data']['object'])
            
            elif event['type'] == 'customer.subscription.updated':
                self._handle_subscription_updated(event['data']['object'])
            
            elif event['type'] == 'customer.subscription.deleted':
                self._handle_subscription_deleted(event['data']['object'])
            
            elif event['type'] == 'invoice.payment_succeeded':
                self._handle_payment_succeeded(event['data']['object'])
            
            elif event['type'] == 'invoice.payment_failed':
                self._handle_payment_failed(event['data']['object'])
            
            billing_event.processed = True
            billing_event.processed_at = datetime.now()
            billing_event.save()
            
        except Exception as e:
            logger.error(f"Error processing webhook {event['type']}: {str(e)}")
            billing_event.error_message = str(e)
            billing_event.save()
            return HttpResponse(status=500)
        
        return HttpResponse(status=200)
    
    def _handle_checkout_completed(self, session):
        """Handle successful checkout completion."""
        tenant_id = session.get('metadata', {}).get('tenant_id')
        if not tenant_id:
            logger.error("No tenant_id in checkout session metadata")
            return
        
        tenant = Tenant.objects.get(id=tenant_id)
        
        # Get the subscription from Stripe
        subscription_id = session.get('subscription')
        if subscription_id:
            stripe_sub = stripe.Subscription.retrieve(subscription_id)
            
            # Update or create local subscription
            subscription, created = Subscription.objects.get_or_create(
                tenant=tenant,
                defaults={
                    'stripe_subscription_id': subscription_id,
                    'stripe_customer_id': session.get('customer'),
                    'status': stripe_sub.status,
                    'plan': self._get_plan_from_stripe_subscription(stripe_sub)
                }
            )
            
            if not created:
                subscription.stripe_subscription_id = subscription_id
                subscription.stripe_customer_id = session.get('customer')
                subscription.status = stripe_sub.status
                subscription.plan = self._get_plan_from_stripe_subscription(stripe_sub)
                subscription.save()
    
    def _handle_subscription_created(self, subscription):
        """Handle subscription creation."""
        customer_id = subscription.get('customer')
        try:
            tenant = Tenant.objects.get(stripe_customer_id=customer_id)
            
            local_subscription, created = Subscription.objects.get_or_create(
                tenant=tenant,
                defaults={
                    'stripe_subscription_id': subscription['id'],
                    'stripe_customer_id': customer_id,
                    'status': subscription['status'],
                    'plan': self._get_plan_from_stripe_subscription(subscription)
                }
            )
            
            tenant.current_plan = local_subscription.plan.slug
            tenant.save()
            
        except Tenant.DoesNotExist:
            logger.error(f"No tenant found for customer {customer_id}")
    
    def _handle_subscription_updated(self, subscription):
        """Handle subscription updates."""
        try:
            local_subscription = Subscription.objects.get(
                stripe_subscription_id=subscription['id']
            )
            local_subscription.status = subscription['status']
            local_subscription.plan = self._get_plan_from_stripe_subscription(subscription)
            local_subscription.save()
            
            local_subscription.tenant.current_plan = local_subscription.plan.slug
            local_subscription.tenant.save()
            
        except Subscription.DoesNotExist:
            logger.error(f"No local subscription found for {subscription['id']}")
    
    def _handle_subscription_deleted(self, subscription):
        """Handle subscription cancellation."""
        try:
            local_subscription = Subscription.objects.get(
                stripe_subscription_id=subscription['id']
            )
            local_subscription.status = 'canceled'
            local_subscription.save()
            
            # Revert to free plan
            free_plan = Plan.objects.get(slug='free')
            local_subscription.plan = free_plan
            local_subscription.save()
            
            local_subscription.tenant.current_plan = 'free'
            local_subscription.tenant.save()
            
        except Subscription.DoesNotExist:
            logger.error(f"No local subscription found for {subscription['id']}")
    
    def _handle_payment_succeeded(self, invoice):
        """Handle successful payment."""
        subscription_id = invoice.get('subscription')
        if subscription_id:
            try:
                local_subscription = Subscription.objects.get(
                    stripe_subscription_id=subscription_id
                )
                local_subscription.status = 'active'
                local_subscription.save()
                
            except Subscription.DoesNotExist:
                logger.error(f"No local subscription found for {subscription_id}")
    
    def _handle_payment_failed(self, invoice):
        """Handle failed payment."""
        subscription_id = invoice.get('subscription')
        if subscription_id:
            try:
                local_subscription = Subscription.objects.get(
                    stripe_subscription_id=subscription_id
                )
                local_subscription.status = 'past_due'
                local_subscription.save()
                
            except Subscription.DoesNotExist:
                logger.error(f"No local subscription found for {subscription_id}")
    
    def _get_plan_from_stripe_subscription(self, stripe_subscription):
        """Get local Plan from Stripe subscription."""
        price_id = stripe_subscription['items']['data'][0]['price']['id']
        try:
            return Plan.objects.get(stripe_price_id=price_id)
        except Plan.DoesNotExist:
            logger.error(f"No plan found for Stripe price {price_id}")
            return Plan.objects.get(slug='free')  # Fallback to free plan