"""
Training Serializers

REST API serializers for security awareness training.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import (
    TrainingCategory,
    TrainingVideo,
    SecurityAwarenessCampaign,
    CampaignDelivery,
    VideoView
)

User = get_user_model()


class TrainingCategorySerializer(serializers.ModelSerializer):
    """Serializer for training categories."""

    videos_count = serializers.SerializerMethodField()

    class Meta:
        model = TrainingCategory
        fields = [
            'id', 'name', 'description', 'color', 'is_active',
            'videos_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_videos_count(self, obj):
        return obj.videos.filter(is_published=True).count()


class TrainingVideoListSerializer(serializers.ModelSerializer):
    """Serializer for training video list view."""

    category_name = serializers.CharField(source='category.name', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TrainingVideo
        fields = [
            'id', 'title', 'description', 'category_name', 'category_color',
            'video_provider', 'duration_minutes', 'difficulty_level',
            'is_published', 'published_at', 'created_by_name', 'view_count',
            'created_at', 'updated_at'
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.email
        return None


class TrainingVideoDetailSerializer(serializers.ModelSerializer):
    """Serializer for training video detail view."""

    category_details = TrainingCategorySerializer(source='category', read_only=True)
    created_by_details = serializers.SerializerMethodField()
    embed_url = serializers.ReadOnlyField()

    class Meta:
        model = TrainingVideo
        fields = [
            'id', 'title', 'description', 'category', 'category_details',
            'video_provider', 'video_url', 'video_id', 'embed_url',
            'duration_minutes', 'difficulty_level', 'is_published',
            'published_at', 'created_by', 'created_by_details', 'view_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'view_count', 'published_at', 'created_at', 'updated_at']

    def get_created_by_details(self, obj):
        if obj.created_by:
            return {
                'id': str(obj.created_by.id),
                'name': f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.email,
                'email': obj.created_by.email
            }
        return None

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class SecurityAwarenessCampaignListSerializer(serializers.ModelSerializer):
    """Serializer for campaign list view."""

    created_by_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    target_users_count = serializers.SerializerMethodField()

    class Meta:
        model = SecurityAwarenessCampaign
        fields = [
            'id', 'name', 'description', 'subject_line', 'is_active',
            'send_frequency', 'start_date', 'end_date', 'next_send_date',
            'send_to_all_users', 'target_users_count', 'created_by_name',
            'total_sent', 'total_opened', 'total_clicked', 'open_rate',
            'click_rate', 'status', 'created_at', 'updated_at'
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.email
        return None

    def get_status(self, obj):
        if not obj.is_active:
            return 'inactive'
        elif obj.end_date and obj.end_date < timezone.now():
            return 'ended'
        elif obj.start_date > timezone.now():
            return 'scheduled'
        elif obj.is_due_to_send():
            return 'ready_to_send'
        else:
            return 'active'

    def get_target_users_count(self, obj):
        if obj.send_to_all_users:
            return User.objects.filter(is_active=True).count()
        return obj.target_users.count()


class SecurityAwarenessCampaignDetailSerializer(serializers.ModelSerializer):
    """Serializer for campaign detail view."""

    created_by_details = serializers.SerializerMethodField()
    target_users_details = serializers.SerializerMethodField()
    recent_deliveries = serializers.SerializerMethodField()
    analytics = serializers.SerializerMethodField()

    class Meta:
        model = SecurityAwarenessCampaign
        fields = [
            'id', 'name', 'description', 'subject_line', 'email_content',
            'is_active', 'send_frequency', 'start_date', 'end_date',
            'next_send_date', 'send_to_all_users', 'target_users',
            'created_by', 'created_by_details', 'target_users_details',
            'total_sent', 'total_opened', 'total_clicked', 'open_rate',
            'click_rate', 'recent_deliveries', 'analytics',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'created_by', 'total_sent', 'total_opened', 'total_clicked',
            'open_rate', 'click_rate', 'created_at', 'updated_at'
        ]

    def get_created_by_details(self, obj):
        if obj.created_by:
            return {
                'id': str(obj.created_by.id),
                'name': f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.email,
                'email': obj.created_by.email
            }
        return None

    def get_target_users_details(self, obj):
        if obj.send_to_all_users:
            return {'type': 'all_users', 'count': User.objects.filter(is_active=True).count()}
        else:
            users = obj.target_users.all()[:10]  # Limit to first 10 for performance
            return {
                'type': 'specific_users',
                'count': obj.target_users.count(),
                'users': [
                    {
                        'id': str(user.id),
                        'name': f"{user.first_name} {user.last_name}".strip() or user.email,
                        'email': user.email
                    }
                    for user in users
                ]
            }

    def get_recent_deliveries(self, obj):
        recent = obj.deliveries.select_related('user')[:5]
        return [
            {
                'id': str(delivery.id),
                'user_email': delivery.user.email,
                'sent_at': delivery.sent_at,
                'delivery_status': delivery.delivery_status,
                'opened_at': delivery.opened_at,
                'clicked_at': delivery.clicked_at
            }
            for delivery in recent
        ]

    def get_analytics(self, obj):
        from django.utils import timezone
        from datetime import timedelta

        # Get analytics for the last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_deliveries = obj.deliveries.filter(sent_at__gte=thirty_days_ago)

        return {
            'recent_sent': recent_deliveries.count(),
            'recent_opened': recent_deliveries.filter(opened_at__isnull=False).count(),
            'recent_clicked': recent_deliveries.filter(clicked_at__isnull=False).count(),
            'recent_bounced': recent_deliveries.filter(delivery_status='bounced').count(),
            'recent_failed': recent_deliveries.filter(delivery_status='failed').count()
        }

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class CampaignDeliverySerializer(serializers.ModelSerializer):
    """Serializer for campaign delivery tracking."""

    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = CampaignDelivery
        fields = [
            'id', 'campaign', 'campaign_name', 'user', 'user_email', 'user_name',
            'sent_at', 'opened_at', 'clicked_at', 'email_subject',
            'recipient_email', 'delivery_status'
        ]
        read_only_fields = ['sent_at']

    def get_user_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email
        return None


class VideoViewSerializer(serializers.ModelSerializer):
    """Serializer for video view tracking."""

    video_title = serializers.CharField(source='video.title', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = VideoView
        fields = [
            'id', 'video', 'video_title', 'user', 'user_email',
            'started_at', 'duration_watched', 'completed', 'completion_percentage'
        ]
        read_only_fields = ['started_at']

    def create(self, validated_data):
        # Get user from request context
        if 'request' in self.context:
            validated_data['user'] = self.context['request'].user

            # Get IP address and user agent from request
            request = self.context['request']
            validated_data['ip_address'] = self.get_client_ip(request)
            validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')

        return super().create(validated_data)

    def get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class TrainingAnalyticsSerializer(serializers.Serializer):
    """Serializer for training module analytics."""

    total_videos = serializers.IntegerField()
    total_categories = serializers.IntegerField()
    total_campaigns = serializers.IntegerField()
    active_campaigns = serializers.IntegerField()

    # Video analytics
    most_watched_videos = serializers.ListField()
    video_completion_rate = serializers.FloatField()
    total_video_views = serializers.IntegerField()

    # Campaign analytics
    total_emails_sent = serializers.IntegerField()
    average_open_rate = serializers.FloatField()
    average_click_rate = serializers.FloatField()
    campaigns_due_to_send = serializers.IntegerField()

    # Recent activity
    recent_video_views = serializers.ListField()
    recent_campaign_deliveries = serializers.ListField()