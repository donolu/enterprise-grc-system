"""
Policy Repository Serializers

Comprehensive serialization for policy management, versioning, and acknowledgments.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import (
    PolicyCategory, Policy, PolicyVersion,
    PolicyAcknowledgment, PolicyDistribution, PolicyVersionAuditLog
)

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user information for policy context."""

    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name']
        read_only_fields = ['id', 'email', 'first_name', 'last_name', 'full_name']


class PolicyCategorySerializer(serializers.ModelSerializer):
    """Serializer for policy categories."""

    policies_count = serializers.SerializerMethodField()

    class Meta:
        model = PolicyCategory
        fields = [
            'id', 'name', 'description', 'color',
            'policies_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_policies_count(self, obj):
        """Get count of policies in this category."""
        return obj.policies.filter(status__in=['approved', 'under_review']).count()


class PolicyVersionListSerializer(serializers.ModelSerializer):
    """List serializer for policy versions."""

    created_by_details = UserBasicSerializer(source='created_by', read_only=True)
    approved_by_details = UserBasicSerializer(source='approved_by', read_only=True)
    file_name = serializers.CharField(read_only=True)
    file_extension = serializers.CharField(read_only=True)
    is_current = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = PolicyVersion
        fields = [
            'id', 'version_number', 'summary', 'is_active', 'is_published',
            'lifecycle_state', 'document_size', 'final_pdf_size',
            'file_name', 'file_extension', 'is_current', 'is_expired',
            'effective_date', 'expiry_date', 'approved_at', 'created_at',
            'finalized_at', 'created_by_details', 'approved_by_details'
        ]
        read_only_fields = [
            'id', 'document_size', 'file_name', 'file_extension',
            'is_current', 'is_expired', 'created_at'
        ]


class PolicyListSerializer(serializers.ModelSerializer):
    """List serializer for policies."""

    category_name = serializers.CharField(source='category.name', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    owner_details = UserBasicSerializer(source='owner', read_only=True)
    current_version = PolicyVersionListSerializer(read_only=True)
    versions_count = serializers.SerializerMethodField()
    acknowledgment_count = serializers.SerializerMethodField()
    is_due_for_review = serializers.BooleanField(read_only=True)

    class Meta:
        model = Policy
        fields = [
            'id', 'policy_code', 'title', 'policy_type', 'status',
            'category_name', 'category_color', 'owner_details', 'current_version',
            'review_frequency_months', 'next_review_date', 'requires_acknowledgment',
            'acknowledgment_validity_days', 'versions_count', 'acknowledgment_count',
            'is_due_for_review', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'policy_code', 'category_name', 'category_color',
            'current_version', 'versions_count', 'acknowledgment_count',
            'is_due_for_review', 'created_at', 'updated_at'
        ]

    def get_versions_count(self, obj):
        """Get count of versions for this policy."""
        return obj.versions.count()

    def get_acknowledgment_count(self, obj):
        """Get count of acknowledgments for current version."""
        current_version = obj.current_version
        if current_version:
            return current_version.acknowledgments.count()
        return 0


class PolicyVersionDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for policy versions."""

    policy_details = PolicyListSerializer(source='policy', read_only=True)
    created_by_details = UserBasicSerializer(source='created_by', read_only=True)
    approved_by_details = UserBasicSerializer(source='approved_by', read_only=True)
    file_name = serializers.CharField(read_only=True)
    file_extension = serializers.CharField(read_only=True)
    is_current = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    acknowledgments_count = serializers.SerializerMethodField()
    finalized_by_details = UserBasicSerializer(source='finalized_by', read_only=True)

    class Meta:
        model = PolicyVersion
        fields = [
            'id', 'policy', 'policy_details', 'version_number', 'document',
            'document_size', 'final_pdf', 'final_pdf_size',
            'file_name', 'file_extension', 'summary', 'lifecycle_state',
            'is_active', 'is_published', 'is_current', 'is_expired',
            'approved_at', 'effective_date', 'expiry_date',
            'finalized_at', 'acknowledgments_count', 'created_at',
            'created_by_details', 'approved_by_details', 'finalized_by_details'
        ]
        read_only_fields = [
            'id', 'document_size', 'final_pdf', 'final_pdf_size',
            'file_name', 'file_extension', 'finalized_at',
            'is_current', 'is_expired', 'acknowledgments_count', 'created_at'
        ]

    def get_acknowledgments_count(self, obj):
        """Get count of acknowledgments for this version."""
        return obj.acknowledgments.count()

    def validate_document(self, value):
        """Validate uploaded document."""
        if value:
            if self.instance and self.instance.lifecycle_state == 'final':
                raise serializers.ValidationError(
                    "Finalised policy versions cannot replace the editable source document."
                )

            # Check file size (max 50MB)
            if value.size > 50 * 1024 * 1024:
                raise serializers.ValidationError(
                    "File size cannot exceed 50MB."
                )

            # Check file extension
            allowed_extensions = ['pdf', 'docx', 'doc']
            file_extension = value.name.split('.')[-1].lower()
            if file_extension not in allowed_extensions:
                raise serializers.ValidationError(
                    f"File type not supported. Allowed: {', '.join(allowed_extensions)}"
                )

        return value


class PolicyVersionAuditLogSerializer(serializers.ModelSerializer):
    actor_details = UserBasicSerializer(source='actor', read_only=True)

    class Meta:
        model = PolicyVersionAuditLog
        fields = [
            'id', 'policy_version', 'action', 'actor', 'actor_details',
            'details', 'created_at'
        ]
        read_only_fields = fields


class PolicyDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for policies."""

    category_details = PolicyCategorySerializer(source='category', read_only=True)
    owner_details = UserBasicSerializer(source='owner', read_only=True)
    approver_details = UserBasicSerializer(source='approver', read_only=True)
    created_by_details = UserBasicSerializer(source='created_by', read_only=True)
    versions = PolicyVersionListSerializer(many=True, read_only=True)
    current_version = PolicyVersionListSerializer(read_only=True)
    latest_version = PolicyVersionListSerializer(read_only=True)
    is_due_for_review = serializers.BooleanField(read_only=True)
    acknowledgment_stats = serializers.SerializerMethodField()

    class Meta:
        model = Policy
        fields = [
            'id', 'policy_code', 'title', 'category', 'category_details',
            'policy_type', 'status', 'owner', 'owner_details',
            'approver', 'approver_details', 'review_frequency_months',
            'next_review_date', 'requires_acknowledgment', 'acknowledgment_validity_days',
            'versions', 'current_version', 'latest_version', 'is_due_for_review',
            'acknowledgment_stats', 'created_at', 'updated_at', 'created_by_details'
        ]
        read_only_fields = [
            'id', 'policy_code', 'current_version', 'latest_version',
            'is_due_for_review', 'acknowledgment_stats', 'created_at', 'updated_at'
        ]

    def get_acknowledgment_stats(self, obj):
        """Get acknowledgment statistics for current version."""
        current_version = obj.current_version
        if not current_version:
            return {
                'total_acknowledgments': 0,
                'pending_acknowledgments': 0,
                'acknowledgment_rate': 0.0
            }

        total_acks = current_version.acknowledgments.count()
        total_distributions = current_version.distributions.count()

        return {
            'total_acknowledgments': total_acks,
            'total_distributions': total_distributions,
            'pending_acknowledgments': max(0, total_distributions - total_acks),
            'acknowledgment_rate': (total_acks / total_distributions * 100) if total_distributions > 0 else 0.0
        }


class PolicyCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating policies."""

    class Meta:
        model = Policy
        fields = [
            'title', 'category', 'policy_type', 'owner', 'approver',
            'review_frequency_months', 'next_review_date',
            'requires_acknowledgment', 'acknowledgment_validity_days'
        ]

    def validate_next_review_date(self, value):
        """Validate next review date is in the future."""
        if value and value <= timezone.now().date():
            raise serializers.ValidationError(
                "Next review date must be in the future."
            )
        return value


class PolicyAcknowledgmentSerializer(serializers.ModelSerializer):
    """Serializer for policy acknowledgments."""

    user_details = UserBasicSerializer(source='user', read_only=True)
    policy_version_details = PolicyVersionListSerializer(source='policy_version', read_only=True)
    policy_title = serializers.CharField(source='policy_version.policy.title', read_only=True)
    policy_code = serializers.CharField(source='policy_version.policy.policy_code', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = PolicyAcknowledgment
        fields = [
            'id', 'user', 'user_details', 'policy_version', 'policy_version_details',
            'policy_title', 'policy_code', 'acknowledged_at', 'expires_at',
            'ip_address', 'user_agent', 'is_expired', 'is_valid'
        ]
        read_only_fields = [
            'id', 'acknowledged_at', 'expires_at', 'is_expired', 'is_valid'
        ]


class PolicyAcknowledgmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating policy acknowledgments."""

    class Meta:
        model = PolicyAcknowledgment
        fields = ['policy_version']

    def create(self, validated_data):
        """Create acknowledgment with request context."""
        request = self.context.get('request')
        validated_data['user'] = request.user

        # Capture request metadata
        if request:
            validated_data['ip_address'] = request.META.get('REMOTE_ADDR')
            validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')[:500]

        return super().create(validated_data)


class PolicyDistributionSerializer(serializers.ModelSerializer):
    """Serializer for policy distributions."""

    policy_version_details = PolicyVersionListSerializer(source='policy_version', read_only=True)
    distributed_to_details = UserBasicSerializer(source='distributed_to', read_only=True)
    distributed_by_details = UserBasicSerializer(source='distributed_by', read_only=True)
    policy_title = serializers.CharField(source='policy_version.policy.title', read_only=True)
    policy_code = serializers.CharField(source='policy_version.policy.policy_code', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = PolicyDistribution
        fields = [
            'id', 'policy_version', 'policy_version_details', 'policy_title', 'policy_code',
            'distributed_to', 'distributed_to_details', 'distributed_by', 'distributed_by_details',
            'distributed_at', 'notification_sent', 'notification_sent_at',
            'reminder_count', 'last_reminder_sent', 'acknowledged', 'acknowledged_at',
            'is_overdue'
        ]
        read_only_fields = [
            'id', 'distributed_at', 'notification_sent_at', 'last_reminder_sent',
            'acknowledged_at', 'is_overdue'
        ]


class PolicySummarySerializer(serializers.Serializer):
    """Serializer for policy repository summary statistics."""

    total_policies = serializers.IntegerField()
    active_policies = serializers.IntegerField()
    draft_policies = serializers.IntegerField()
    policies_due_review = serializers.IntegerField()
    total_versions = serializers.IntegerField()
    total_acknowledgments = serializers.IntegerField()
    acknowledgment_rate = serializers.FloatField()
    categories_count = serializers.IntegerField()
    recent_activities = serializers.ListSerializer(child=serializers.DictField())
