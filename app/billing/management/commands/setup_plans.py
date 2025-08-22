import stripe
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Plan


class Command(BaseCommand):
    help = 'Set up subscription plans in both database and Stripe'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-stripe-products',
            action='store_true',
            help='Create products and prices in Stripe',
        )

    def handle(self, *args, **options):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        
        plans_data = [
            {
                'name': 'Free',
                'slug': 'free',
                'description': 'Perfect for getting started with basic GRC needs',
                'price_monthly': 0,
                'max_users': 3,
                'max_documents': 50,
                'max_frameworks': 1,
                'has_api_access': False,
                'has_advanced_reporting': False,
                'has_priority_support': False,
            },
            {
                'name': 'Basic',
                'slug': 'basic',
                'description': 'Ideal for small to medium teams with growing compliance needs',
                'price_monthly': 49,
                'max_users': 10,
                'max_documents': 500,
                'max_frameworks': 5,
                'has_api_access': True,
                'has_advanced_reporting': False,
                'has_priority_support': False,
            },
            {
                'name': 'Enterprise',
                'slug': 'enterprise',
                'description': 'Full-featured solution for large organizations',
                'price_monthly': 199,
                'max_users': 100,
                'max_documents': 10000,
                'max_frameworks': 999,
                'has_api_access': True,
                'has_advanced_reporting': True,
                'has_priority_support': True,
            }
        ]
        
        for plan_data in plans_data:
            # Create or update local plan
            plan, created = Plan.objects.get_or_create(
                slug=plan_data['slug'],
                defaults=plan_data
            )
            
            if not created:
                for key, value in plan_data.items():
                    setattr(plan, key, value)
                plan.save()
            
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} plan: {plan.name}")
            
            # Create Stripe products and prices if requested
            if options['create_stripe_products'] and plan.price_monthly > 0:
                try:
                    # Create product in Stripe
                    product = stripe.Product.create(
                        name=plan.name,
                        description=plan.description,
                        metadata={'plan_id': str(plan.id)}
                    )
                    
                    # Create price in Stripe
                    price = stripe.Price.create(
                        unit_amount=int(plan.price_monthly * 100),  # Convert to cents
                        currency='usd',
                        recurring={'interval': 'month'},
                        product=product.id,
                        metadata={'plan_id': str(plan.id)}
                    )
                    
                    # Update plan with Stripe price ID
                    plan.stripe_price_id = price.id
                    plan.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Created Stripe product and price for {plan.name}: {price.id}"
                        )
                    )
                    
                except stripe.error.StripeError as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Failed to create Stripe product for {plan.name}: {str(e)}"
                        )
                    )
        
        self.stdout.write(self.style.SUCCESS('Successfully set up all plans'))
        
        if options['create_stripe_products']:
            self.stdout.write("\nNext steps:")
            self.stdout.write("1. Copy the Stripe Price IDs to your .env file:")
            for plan in Plan.objects.filter(price_monthly__gt=0):
                if plan.stripe_price_id:
                    env_var = f"STRIPE_PRICE_{plan.slug.upper()}"
                    self.stdout.write(f"   {env_var}={plan.stripe_price_id}")
            self.stdout.write("2. Set up webhook endpoint in Stripe dashboard")
            self.stdout.write("   URL: https://yourdomain.com/webhooks/stripe/")
            self.stdout.write("   Events: customer.subscription.*, invoice.*, checkout.session.completed")