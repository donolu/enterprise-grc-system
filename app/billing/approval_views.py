from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from django_tenants.utils import schema_context

from core.models import LimitOverrideRequest, Tenant, Subscription
from .audit import (
    audit_limit_override_change,
    audit_subscription_change,
    billing_changed_values,
    snapshot_limit_override,
    snapshot_subscription,
)
from .approval_serializers import (
    LimitOverrideRequestSerializer, 
    LimitOverrideCreateSerializer,
    ApprovalActionSerializer
)
from .tenant_access import get_public_tenant


class LimitOverrideRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing limit override requests with approval workflow.
    """
    serializer_class = LimitOverrideRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        Filter override requests based on user role:
        - Tenant users: see their own requests
        - Approvers: see pending requests they can approve
        - Admins: see all requests
        """
        user = self.request.user
        
        # Check if user has approval permissions (implement based on your auth system)
        if self.request.user.is_staff or hasattr(user, 'can_approve_limit_overrides'):
            # Show all requests for approvers/admins
            return LimitOverrideRequest.objects.all()
        else:
            # Show only tenant's own requests
            try:
                tenant = Tenant.objects.get(schema_name=self.request.tenant.schema_name)
                subscription = getattr(tenant, 'subscription', None)
                if subscription:
                    return LimitOverrideRequest.objects.filter(subscription=subscription)
            except Exception:
                pass
            
        return LimitOverrideRequest.objects.none()
    
    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == 'create':
            return LimitOverrideCreateSerializer
        elif self.action in ['approve_first', 'approve_second', 'reject']:
            return ApprovalActionSerializer
        return LimitOverrideRequestSerializer

    def _get_public_override_request(self, pk):
        return LimitOverrideRequest.objects.select_related(
            'subscription__tenant',
            'subscription__plan',
        ).get(pk=pk)
    
    def create(self, request):
        """Create a new limit override request."""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            with schema_context("public"):
                tenant = get_public_tenant(request.tenant.schema_name)
                subscription = getattr(tenant, 'subscription', None)

                if not subscription:
                    return Response(
                        {'error': 'No active subscription found'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Get current limit based on limit type
                limit_type = serializer.validated_data['limit_type']
                if limit_type == 'max_users':
                    current_limit = subscription.get_effective_user_limit()
                elif limit_type == 'max_documents':
                    current_limit = subscription.get_effective_document_limit()
                elif limit_type == 'max_frameworks':
                    current_limit = subscription.get_effective_framework_limit()
                elif limit_type == 'max_storage_gb':
                    current_limit = subscription.get_effective_storage_limit()
                else:
                    return Response(
                        {'error': 'Invalid limit type'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                override_request = serializer.save(
                    subscription=subscription,
                    current_limit=current_limit,
                    requested_by=f"{request.user.username} ({request.user.email})"
                )
                audit_limit_override_change(
                    event='LIMIT_OVERRIDE_REQUESTED',
                    override_request=override_request,
                    actor=request.user,
                    request=request,
                    new=snapshot_limit_override(override_request),
                    source={'type': 'api', 'reference': 'limit_override.create'},
                )
                response_data = LimitOverrideRequestSerializer(override_request).data

                # TODO: Send notification to approvers
                # self._send_approval_notification(override_request)

                return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': 'Failed to create override request'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def approve_first(self, request, pk=None):
        """Provide first approval for limit override request."""
        # Check permissions - implement based on your auth system
        if not (request.user.is_staff or hasattr(request.user, 'can_approve_limit_overrides')):
            return Response(
                {'error': 'Insufficient permissions'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        approver_name = f"{request.user.username} ({request.user.email})"
        notes = serializer.validated_data.get('notes', '')

        with schema_context("public"):
            override_request = self._get_public_override_request(pk)
            previous = snapshot_limit_override(override_request)
            if override_request.approve_first(approver_name, notes):
                new = snapshot_limit_override(override_request)
                previous_changed, new_changed = billing_changed_values(previous, new)
                audit_limit_override_change(
                    event='LIMIT_OVERRIDE_FIRST_APPROVED',
                    override_request=override_request,
                    actor=request.user,
                    request=request,
                    previous=previous_changed,
                    new=new_changed,
                    reason=notes,
                    source={'type': 'api', 'reference': 'limit_override.approve_first'},
                )
                # TODO: Send notification about first approval
                # self._send_second_approval_notification(override_request)

                return Response({
                    'message': 'First approval recorded successfully',
                    'status': 'needs_second_approval',
                    'first_approver': approver_name,
                    'notes': notes
                })
            return Response(
                {'error': 'Request cannot be approved at this stage'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def approve_second(self, request, pk=None):
        """Provide second approval for limit override request."""
        # Check permissions
        if not (request.user.is_staff or hasattr(request.user, 'can_approve_limit_overrides')):
            return Response(
                {'error': 'Insufficient permissions'}, 
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        current_user = f"{request.user.username} ({request.user.email})"
        notes = serializer.validated_data.get('notes', '')

        with schema_context("public"):
            override_request = self._get_public_override_request(pk)
            if override_request.first_approver == current_user:
                return Response(
                    {'error': 'Cannot provide second approval - you already gave first approval'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            previous = snapshot_limit_override(override_request)
            if override_request.approve_second(current_user, notes):
                new = snapshot_limit_override(override_request)
                previous_changed, new_changed = billing_changed_values(previous, new)
                audit_limit_override_change(
                    event='LIMIT_OVERRIDE_APPROVED',
                    override_request=override_request,
                    actor=request.user,
                    request=request,
                    previous=previous_changed,
                    new=new_changed,
                    reason=notes,
                    source={'type': 'api', 'reference': 'limit_override.approve_second'},
                )
                # TODO: Send notification about final approval
                # self._send_final_approval_notification(override_request)

                return Response({
                    'message': 'Second approval recorded - request fully approved',
                    'status': 'approved',
                    'second_approver': current_user,
                    'notes': notes,
                    'can_be_applied': True
                })
            return Response(
                {'error': 'Request cannot be approved at this stage'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a limit override request."""
        # Check permissions
        if not (request.user.is_staff or hasattr(request.user, 'can_approve_limit_overrides')):
            return Response(
                {'error': 'Insufficient permissions'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        reason = serializer.validated_data.get('rejection_reason', '')
        if not reason:
            return Response(
                {'error': 'Rejection reason is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        rejector_name = f"{request.user.username} ({request.user.email})"

        with schema_context("public"):
            override_request = self._get_public_override_request(pk)
            previous = snapshot_limit_override(override_request)
            if override_request.reject(rejector_name, reason):
                new = snapshot_limit_override(override_request)
                previous_changed, new_changed = billing_changed_values(previous, new)
                audit_limit_override_change(
                    event='LIMIT_OVERRIDE_REJECTED',
                    override_request=override_request,
                    actor=request.user,
                    request=request,
                    previous=previous_changed,
                    new=new_changed,
                    reason=reason,
                    source={'type': 'api', 'reference': 'limit_override.reject'},
                )
                # TODO: Send rejection notification
                # self._send_rejection_notification(override_request)

                return Response({
                    'message': 'Request rejected successfully',
                    'status': 'rejected',
                    'rejected_by': rejector_name,
                    'reason': reason
                })
            return Response(
                {'error': 'Failed to reject request'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def apply_override(self, request, pk=None):
        """Apply an approved limit override to the subscription."""
        # Check permissions - typically only admins can apply
        if not request.user.is_staff:
            return Response(
                {'error': 'Only administrators can apply overrides'}, 
                status=status.HTTP_403_FORBIDDEN
            )

        applied_by = f"{request.user.username} ({request.user.email})"

        with schema_context("public"):
            override_request = self._get_public_override_request(pk)
            if not override_request.can_be_applied:
                return Response(
                    {'error': 'Override cannot be applied - not fully approved'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            previous_override = snapshot_limit_override(override_request)
            previous_subscription = snapshot_subscription(override_request.subscription)
            if override_request.apply_override(applied_by):
                override_request.refresh_from_db()
                override_request.subscription.refresh_from_db()
                new_override = snapshot_limit_override(override_request)
                new_subscription = snapshot_subscription(override_request.subscription)
                previous_changed, new_changed = billing_changed_values(
                    previous_override,
                    new_override,
                )
                audit_limit_override_change(
                    event='LIMIT_OVERRIDE_APPLIED',
                    override_request=override_request,
                    actor=request.user,
                    request=request,
                    previous=previous_changed,
                    new=new_changed,
                    source={'type': 'api', 'reference': 'limit_override.apply'},
                    details={
                        'limit_type': override_request.limit_type,
                        'previous_limit': override_request.current_limit,
                        'new_limit': override_request.requested_limit,
                    },
                )
                previous_sub_changed, new_sub_changed = billing_changed_values(
                    previous_subscription,
                    new_subscription,
                )
                audit_subscription_change(
                    event='SUBSCRIPTION_LIMITS_UPDATED',
                    subscription=override_request.subscription,
                    actor=request.user,
                    request=request,
                    previous=previous_sub_changed,
                    new=new_sub_changed,
                    source={'type': 'api', 'reference': 'limit_override.apply'},
                    details={'override_request_id': override_request.id},
                )
                return Response({
                    'message': 'Override applied successfully',
                    'status': 'applied',
                    'applied_by': applied_by,
                    'new_limit': override_request.requested_limit
                })
            return Response(
                {'error': 'Failed to apply override'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        """Get all requests pending approval for the current user."""
        if not (request.user.is_staff or hasattr(request.user, 'can_approve_limit_overrides')):
            return Response(
                {'error': 'Insufficient permissions'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get requests that need approval
        pending_requests = LimitOverrideRequest.objects.filter(
            Q(status='pending') & 
            (Q(first_approved_at__isnull=True) | 
             Q(first_approved_at__isnull=False, second_approved_at__isnull=True))
        ).order_by('urgency', '-requested_at')
        
        serializer = self.get_serializer(pending_requests, many=True)
        return Response({
            'pending_requests': serializer.data,
            'total_count': pending_requests.count(),
            'needs_first_approval': pending_requests.filter(first_approved_at__isnull=True).count(),
            'needs_second_approval': pending_requests.filter(
                first_approved_at__isnull=False, 
                second_approved_at__isnull=True
            ).count()
        })
    
    @action(detail=False, methods=['get'])
    def approved_pending_application(self, request):
        """Get all fully approved requests pending application."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only administrators can view this'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        approved_requests = LimitOverrideRequest.objects.filter(status='approved')
        serializer = self.get_serializer(approved_requests, many=True)
        return Response({
            'approved_requests': serializer.data,
            'total_count': approved_requests.count()
        })
