"""
Training Views

REST API views for security awareness training.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from django.db.models import Count, Avg, Q, Sum
from django.db import models
from datetime import timedelta

from .models import (
    TrainingCategory,
    TrainingVideo,
    SecurityAwarenessCampaign,
    CampaignDelivery,
    VideoView
)
from .serializers import (
    TrainingCategorySerializer,
    TrainingVideoListSerializer,
    TrainingVideoDetailSerializer,
    SecurityAwarenessCampaignListSerializer,
    SecurityAwarenessCampaignDetailSerializer,
    CampaignDeliverySerializer,
    VideoViewSerializer,
    TrainingAnalyticsSerializer
)
from .filters import TrainingVideoFilter, CampaignFilter


class TrainingCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing training categories.
    """
    queryset = TrainingCategory.objects.all()
    serializer_class = TrainingCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class TrainingVideoViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing training videos.
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = TrainingVideoFilter
    search_fields = ['title', 'description', 'category__name']
    ordering_fields = ['title', 'created_at', 'view_count', 'duration_minutes']
    ordering = ['-created_at']

    def get_queryset(self):
        # Staff can see all videos, regular users only published ones
        if self.request.user.is_staff:
            return TrainingVideo.objects.select_related('category', 'created_by').all()
        else:
            return TrainingVideo.objects.select_related('category', 'created_by').filter(
                is_published=True
            )

    def get_serializer_class(self):
        if self.action == 'list':
            return TrainingVideoListSerializer
        else:
            return TrainingVideoDetailSerializer

    @action(detail=True, methods=['post'])
    def track_view(self, request, pk=None):
        """Track a video view."""
        video = self.get_object()

        # Get view data from request
        duration_watched = request.data.get('duration_watched', 0)
        completed = request.data.get('completed', False)
        completion_percentage = request.data.get('completion_percentage', 0)

        # Create or update view record
        view_data = {
            'video': video.id,
            'duration_watched': duration_watched,
            'completed': completed,
            'completion_percentage': completion_percentage
        }

        serializer = VideoViewSerializer(data=view_data, context={'request': request})
        if serializer.is_valid():
            serializer.save()

            # Update video view count
            video.view_count += 1
            video.save(update_fields=['view_count'])

            return Response({
                'message': 'Video view tracked successfully',
                'view': serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get video analytics."""
        videos = self.get_queryset()

        # Basic stats
        total_videos = videos.count()
        published_videos = videos.filter(is_published=True).count()
        total_views = videos.aggregate(total=Count('views'))['total'] or 0

        # Most watched videos
        most_watched = videos.annotate(
            views_count=Count('views')
        ).order_by('-views_count')[:5]

        most_watched_data = [
            {
                'id': str(video.id),
                'title': video.title,
                'view_count': video.view_count,
                'category': video.category.name
            }
            for video in most_watched
        ]

        # Completion rate
        completion_rate = VideoView.objects.filter(
            video__in=videos,
            completed=True
        ).count()
        total_video_views = VideoView.objects.filter(video__in=videos).count()
        completion_percentage = (
            (completion_rate / total_video_views * 100) if total_video_views > 0 else 0
        )

        return Response({
            'total_videos': total_videos,
            'published_videos': published_videos,
            'total_views': total_views,
            'completion_rate': round(completion_percentage, 1),
            'most_watched_videos': most_watched_data
        })


class SecurityAwarenessCampaignViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing security awareness campaigns.
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CampaignFilter
    search_fields = ['name', 'description', 'subject_line']
    ordering_fields = ['name', 'created_at', 'next_send_date', 'total_sent']
    ordering = ['-created_at']

    def get_queryset(self):
        return SecurityAwarenessCampaign.objects.select_related('created_by').prefetch_related(
            'target_users', 'deliveries'
        ).all()

    def get_serializer_class(self):
        if self.action == 'list':
            return SecurityAwarenessCampaignListSerializer
        else:
            return SecurityAwarenessCampaignDetailSerializer

    @action(detail=True, methods=['post'])
    def send_now(self, request, pk=None):
        """Send campaign immediately."""
        campaign = self.get_object()

        if not campaign.is_active:
            return Response(
                {'error': 'Campaign is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Queue campaign for sending
        from .tasks import send_awareness_campaign
        task = send_awareness_campaign.delay(str(campaign.id))

        return Response({
            'message': 'Campaign queued for sending',
            'task_id': task.id
        })

    @action(detail=True, methods=['post'])
    def test_send(self, request, pk=None):
        """Send test email to current user."""
        campaign = self.get_object()

        # Send test email to requesting user
        from .tasks import send_test_awareness_email
        task = send_test_awareness_email.delay(str(campaign.id), str(request.user.id))

        return Response({
            'message': f'Test email sent to {request.user.email}',
            'task_id': task.id
        })

    @action(detail=False, methods=['get'])
    def due_to_send(self, request):
        """Get campaigns due to send."""
        due_campaigns = self.get_queryset().filter(
            is_active=True,
            next_send_date__lte=timezone.now()
        )

        if self.request.user.is_staff:
            due_campaigns = due_campaigns.filter(
                Q(end_date__isnull=True) | Q(end_date__gt=timezone.now())
            )

        serializer = SecurityAwarenessCampaignListSerializer(due_campaigns, many=True)
        return Response({
            'count': due_campaigns.count(),
            'campaigns': serializer.data
        })

    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get campaign analytics."""
        campaigns = self.get_queryset()

        # Basic stats
        total_campaigns = campaigns.count()
        active_campaigns = campaigns.filter(is_active=True).count()
        total_sent = campaigns.aggregate(total=models.Sum('total_sent'))['total'] or 0

        # Calculate average rates
        campaigns_with_sends = campaigns.filter(total_sent__gt=0)
        avg_open_rate = campaigns_with_sends.aggregate(
            avg=Avg('total_opened') / Avg('total_sent') * 100
        )['avg'] or 0
        avg_click_rate = campaigns_with_sends.aggregate(
            avg=Avg('total_clicked') / Avg('total_sent') * 100
        )['avg'] or 0

        # Recent activity
        recent_deliveries = CampaignDelivery.objects.select_related(
            'campaign', 'user'
        ).order_by('-sent_at')[:10]

        recent_deliveries_data = [
            {
                'id': str(delivery.id),
                'campaign_name': delivery.campaign.name,
                'user_email': delivery.user.email,
                'sent_at': delivery.sent_at,
                'delivery_status': delivery.delivery_status
            }
            for delivery in recent_deliveries
        ]

        return Response({
            'total_campaigns': total_campaigns,
            'active_campaigns': active_campaigns,
            'total_emails_sent': total_sent,
            'average_open_rate': round(avg_open_rate, 1),
            'average_click_rate': round(avg_click_rate, 1),
            'recent_deliveries': recent_deliveries_data
        })


class CampaignDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing campaign deliveries.
    """
    queryset = CampaignDelivery.objects.select_related('campaign', 'user').all()
    serializer_class = CampaignDeliverySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['campaign__name', 'user__email', 'recipient_email']
    ordering_fields = ['sent_at', 'opened_at', 'clicked_at']
    ordering = ['-sent_at']

    @action(detail=True, methods=['post'])
    def mark_opened(self, request, pk=None):
        """Mark delivery as opened (for email tracking)."""
        delivery = self.get_object()

        if not delivery.opened_at:
            delivery.opened_at = timezone.now()
            delivery.delivery_status = 'opened'
            delivery.save()

            # Update campaign stats
            campaign = delivery.campaign
            campaign.total_opened += 1
            campaign.save(update_fields=['total_opened'])

        return Response({'message': 'Delivery marked as opened'})

    @action(detail=True, methods=['post'])
    def mark_clicked(self, request, pk=None):
        """Mark delivery as clicked (for link tracking)."""
        delivery = self.get_object()

        if not delivery.clicked_at:
            delivery.clicked_at = timezone.now()
            delivery.delivery_status = 'clicked'
            delivery.save()

            # Update campaign stats
            campaign = delivery.campaign
            campaign.total_clicked += 1
            campaign.save(update_fields=['total_clicked'])

        return Response({'message': 'Delivery marked as clicked'})


class VideoViewViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing video view analytics.
    """
    queryset = VideoView.objects.select_related('video', 'user').all()
    serializer_class = VideoViewSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['started_at', 'duration_watched', 'completion_percentage']
    ordering = ['-started_at']

    @action(detail=False, methods=['get'])
    def my_views(self, request):
        """Get current user's video views."""
        user_views = self.get_queryset().filter(user=request.user)
        serializer = self.get_serializer(user_views, many=True)
        return Response(serializer.data)


@action(detail=False, methods=['get'])
def training_dashboard(request):
    """
    Get comprehensive training analytics dashboard.
    """
    if not request.user.is_authenticated:
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Video analytics
    videos = TrainingVideo.objects.all()
    total_videos = videos.count()
    published_videos = videos.filter(is_published=True).count()
    total_video_views = VideoView.objects.count()

    # Campaign analytics
    campaigns = SecurityAwarenessCampaign.objects.all()
    total_campaigns = campaigns.count()
    active_campaigns = campaigns.filter(is_active=True).count()
    campaigns_due = campaigns.filter(
        is_active=True,
        next_send_date__lte=timezone.now()
    ).count()

    # Email analytics
    total_emails_sent = campaigns.aggregate(
        total=models.Sum('total_sent')
    )['total'] or 0

    campaigns_with_sends = campaigns.filter(total_sent__gt=0)
    avg_open_rate = 0
    avg_click_rate = 0

    if campaigns_with_sends.exists():
        total_sent_all = campaigns_with_sends.aggregate(
            total=models.Sum('total_sent')
        )['total']
        total_opened_all = campaigns_with_sends.aggregate(
            total=models.Sum('total_opened')
        )['total'] or 0
        total_clicked_all = campaigns_with_sends.aggregate(
            total=models.Sum('total_clicked')
        )['total'] or 0

        avg_open_rate = (total_opened_all / total_sent_all * 100) if total_sent_all else 0
        avg_click_rate = (total_clicked_all / total_sent_all * 100) if total_sent_all else 0

    dashboard_data = {
        'videos': {
            'total': total_videos,
            'published': published_videos,
            'total_views': total_video_views
        },
        'campaigns': {
            'total': total_campaigns,
            'active': active_campaigns,
            'due_to_send': campaigns_due
        },
        'email_metrics': {
            'total_sent': total_emails_sent,
            'average_open_rate': round(avg_open_rate, 1),
            'average_click_rate': round(avg_click_rate, 1)
        }
    }

    return Response(dashboard_data)