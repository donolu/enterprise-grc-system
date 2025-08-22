from rest_framework import serializers
from core.models import LimitOverrideRequest, Subscription


class LimitOverrideRequestSerializer(serializers.ModelSerializer):
    """Serializer for viewing limit override requests."""
    
    tenant_name = serializers.CharField(source='subscription.tenant.name', read_only=True)
    plan_name = serializers.CharField(source='subscription.plan.name', read_only=True)
    limit_type_display = serializers.CharField(source='get_limit_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    urgency_display = serializers.CharField(source='get_urgency_display', read_only=True)
    
    # Approval status properties
    needs_first_approval = serializers.BooleanField(read_only=True)
    needs_second_approval = serializers.BooleanField(read_only=True)
    is_fully_approved = serializers.BooleanField(read_only=True)
    can_be_applied = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = LimitOverrideRequest
        fields = [
            'id', 'tenant_name', 'plan_name', 'limit_type', 'limit_type_display',
            'current_limit', 'requested_limit', 'business_justification', 
            'urgency', 'urgency_display', 'temporary', 'expires_at',
            'status', 'status_display', 'requested_by', 'requested_at',
            'first_approver', 'first_approved_at', 'first_approval_notes',
            'second_approver', 'second_approved_at', 'second_approval_notes',
            'final_decision_by', 'final_decision_at', 'rejection_reason',
            'applied_at', 'applied_by', 'created_at', 'updated_at',
            'needs_first_approval', 'needs_second_approval', 
            'is_fully_approved', 'can_be_applied'
        ]
        read_only_fields = [
            'id', 'requested_by', 'requested_at', 'first_approver', 
            'first_approved_at', 'second_approver', 'second_approved_at',
            'final_decision_by', 'final_decision_at', 'applied_at', 
            'applied_by', 'created_at', 'updated_at'
        ]


class LimitOverrideCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new limit override requests."""
    
    class Meta:
        model = LimitOverrideRequest
        fields = [
            'limit_type', 'requested_limit', 'business_justification',
            'urgency', 'temporary', 'expires_at'
        ]
    
    def validate_requested_limit(self, value):
        """Ensure requested limit is positive."""
        if value <= 0:
            raise serializers.ValidationError("Requested limit must be greater than 0")
        return value
    
    def validate_business_justification(self, value):
        """Ensure business justification is meaningful."""
        if len(value.strip()) < 20:
            raise serializers.ValidationError(
                "Business justification must be at least 20 characters"
            )
        return value
    
    def validate(self, data):
        """Cross-field validation."""
        # If temporary, expires_at is required
        if data.get('temporary') and not data.get('expires_at'):
            raise serializers.ValidationError({
                'expires_at': 'Expiration date is required for temporary overrides'
            })
        
        # If not temporary, expires_at should be None
        if not data.get('temporary') and data.get('expires_at'):
            raise serializers.ValidationError({
                'expires_at': 'Expiration date should not be set for permanent overrides'
            })
        
        return data


class ApprovalActionSerializer(serializers.Serializer):
    """Serializer for approval/rejection actions."""
    
    notes = serializers.CharField(
        required=False, 
        allow_blank=True,
        max_length=1000,
        help_text="Optional notes about the approval/rejection"
    )
    
    rejection_reason = serializers.CharField(
        required=False,
        allow_blank=True, 
        max_length=1000,
        help_text="Required for rejections - explain why the request was rejected"
    )


class LimitOverrideSummarySerializer(serializers.Serializer):
    """Serializer for limit override dashboard summary."""
    
    total_requests = serializers.IntegerField()
    pending_first_approval = serializers.IntegerField()
    pending_second_approval = serializers.IntegerField()
    fully_approved = serializers.IntegerField()
    rejected = serializers.IntegerField()
    applied = serializers.IntegerField()
    
    # Recent requests
    recent_requests = LimitOverrideRequestSerializer(many=True)
    
    # Urgent requests
    urgent_requests = LimitOverrideRequestSerializer(many=True)