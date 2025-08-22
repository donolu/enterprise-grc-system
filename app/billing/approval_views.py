from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q

from core.models import LimitOverrideRequest, Tenant, Subscription
from .approval_serializers import (
    LimitOverrideRequestSerializer, 
    LimitOverrideCreateSerializer,
    ApprovalActionSerializer
)


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
            except:
                pass
            
        return LimitOverrideRequest.objects.none()
    
    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == 'create':
            return LimitOverrideCreateSerializer
        elif self.action in ['approve_first', 'approve_second', 'reject']:
            return ApprovalActionSerializer
        return LimitOverrideRequestSerializer
    
    def create(self, request):
        """Create a new limit override request."""
        try:
            tenant = Tenant.objects.get(schema_name=request.tenant.schema_name)
            subscription = getattr(tenant, 'subscription', None)
            
            if not subscription:
                return Response(
                    {'error': 'No active subscription found'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
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
            
            # Create the override request
            override_request = serializer.save(
                subscription=subscription,
                current_limit=current_limit,
                requested_by=f"{request.user.username} ({request.user.email})"
            )
            
            # TODO: Send notification to approvers
            # self._send_approval_notification(override_request)
            
            return Response(
                LimitOverrideRequestSerializer(override_request).data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {'error': 'Failed to create override request'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def approve_first(self, request, pk=None):
        """Provide first approval for limit override request."""
        override_request = self.get_object()
        
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
        
        if override_request.approve_first(approver_name, notes):
            # TODO: Send notification about first approval
            # self._send_second_approval_notification(override_request)
            
            return Response({
                'message': 'First approval recorded successfully',
                'status': 'needs_second_approval',
                'first_approver': approver_name,
                'notes': notes
            })
        else:
            return Response(
                {'error': 'Request cannot be approved at this stage'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def approve_second(self, request, pk=None):
        """Provide second approval for limit override request."""
        override_request = self.get_object()
        
        # Check permissions
        if not (request.user.is_staff or hasattr(request.user, 'can_approve_limit_overrides')):
            return Response(
                {'error': 'Insufficient permissions'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Prevent same person from giving both approvals
        current_user = f"{request.user.username} ({request.user.email})"
        if override_request.first_approver == current_user:
            return Response(
                {'error': 'Cannot provide second approval - you already gave first approval'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        notes = serializer.validated_data.get('notes', '')
        
        if override_request.approve_second(current_user, notes):
            # TODO: Send notification about final approval
            # self._send_final_approval_notification(override_request)
            
            return Response({
                'message': 'Second approval recorded - request fully approved',
                'status': 'approved',
                'second_approver': current_user,
                'notes': notes,
                'can_be_applied': True
            })
        else:
            return Response(
                {'error': 'Request cannot be approved at this stage'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a limit override request."""
        override_request = self.get_object()
        
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
        
        if override_request.reject(rejector_name, reason):
            # TODO: Send rejection notification
            # self._send_rejection_notification(override_request)
            
            return Response({
                'message': 'Request rejected successfully',
                'status': 'rejected',
                'rejected_by': rejector_name,
                'reason': reason
            })
        else:
            return Response(
                {'error': 'Failed to reject request'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def apply_override(self, request, pk=None):
        """Apply an approved limit override to the subscription."""
        override_request = self.get_object()
        
        # Check permissions - typically only admins can apply
        if not request.user.is_staff:
            return Response(
                {'error': 'Only administrators can apply overrides'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not override_request.can_be_applied:
            return Response(
                {'error': 'Override cannot be applied - not fully approved'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        applied_by = f"{request.user.username} ({request.user.email})"
        
        if override_request.apply_override(applied_by):
            return Response({
                'message': 'Override applied successfully',
                'status': 'applied',
                'applied_by': applied_by,
                'new_limit': override_request.requested_limit
            })
        else:
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