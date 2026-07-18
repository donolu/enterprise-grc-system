"""Training domain service entry points."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Avg, Case, Count, F, FloatField, Q, Sum, Value, When
from django.utils import timezone

from .models import SecurityAwarenessCampaign, TrainingCategory, TrainingVideo, VideoView

User = get_user_model()


class TrainingAnalyticsService:
    """Read-side analytics owned by the training domain."""

    @staticmethod
    def executive_summary():
        total_views = VideoView.objects.count()
        completed_views = VideoView.objects.filter(completed=True).count()
        completion_rate = (
            round((completed_views / total_views) * 100, 1) if total_views > 0 else 0
        )

        return {
            "total_videos": TrainingVideo.objects.count(),
            "total_views": total_views,
            "unique_viewers": VideoView.objects.values("user").distinct().count(),
            "completion_rate": completion_rate,
            "active_campaigns": SecurityAwarenessCampaign.objects.filter(
                is_active=True
            ).count(),
        }

    @staticmethod
    def dashboard_data(now=None):
        today = now or timezone.now().date()
        video_stats = {
            "total_videos": TrainingVideo.objects.count(),
            "total_views": VideoView.objects.count(),
            "unique_viewers": VideoView.objects.values("user").distinct().count(),
            "total_watch_time": VideoView.objects.aggregate(
                total_minutes=Sum("duration_watched")
            )["total_minutes"]
            or 0,
            "avg_completion_rate": VideoView.objects.aggregate(
                avg_completion=Avg("completion_percentage")
            )["avg_completion"]
            or 0,
        }

        category_performance = list(
            TrainingCategory.objects.annotate(
                video_count=Count("videos"),
                total_views=Count("videos__views"),
                avg_completion=Avg("videos__views__completion_percentage"),
                total_watch_time=Sum("videos__views__duration_watched"),
            )
            .values(
                "name",
                "description",
                "color",
                "video_count",
                "total_views",
                "avg_completion",
                "total_watch_time",
            )
            .order_by("-total_views")
        )

        user_engagement = {
            "active_learners_30_days": VideoView.objects.filter(
                started_at__date__gte=today - timedelta(days=30)
            )
            .values("user")
            .distinct()
            .count(),
            "completed_videos_30_days": VideoView.objects.filter(
                started_at__date__gte=today - timedelta(days=30),
                completed=True,
            ).count(),
            "avg_videos_per_user": VideoView.objects.values("user")
            .annotate(video_count=Count("video", distinct=True))
            .aggregate(avg=Avg("video_count"))["avg"]
            or 0,
            "completion_rate": TrainingAnalyticsService.completion_rate_percentage(),
        }

        campaign_stats = list(
            SecurityAwarenessCampaign.objects.annotate(
                engagement_rate=Case(
                    When(total_sent=0, then=Value(0.0)),
                    default=F("total_opened") * 100.0 / F("total_sent"),
                    output_field=FloatField(),
                ),
                click_through_rate=Case(
                    When(total_opened=0, then=Value(0.0)),
                    default=F("total_clicked") * 100.0 / F("total_opened"),
                    output_field=FloatField(),
                ),
            ).values(
                "name",
                "send_frequency",
                "total_sent",
                "total_opened",
                "total_clicked",
                "engagement_rate",
                "click_through_rate",
                "is_active",
            )
        )

        training_trends = list(
            VideoView.objects.filter(started_at__date__gte=today - timedelta(days=180))
            .extra(select={"month": "DATE_TRUNC('month', started_at)"})
            .values("month")
            .annotate(
                views=Count("id"),
                unique_users=Count("user", distinct=True),
                completions=Count("id", filter=Q(completed=True)),
                avg_completion_percentage=Avg("completion_percentage"),
            )
            .order_by("month")
        )

        return {
            "video_engagement": video_stats,
            "category_performance": category_performance,
            "user_engagement": user_engagement,
            "campaign_analytics": campaign_stats,
            "training_trends": training_trends,
            "generated_at": today.isoformat(),
        }

    @staticmethod
    def training_gap_count():
        return User.objects.exclude(video_views__completed=True).count()

    @staticmethod
    def completion_rate_percentage():
        total_views = VideoView.objects.count()
        completed_views = VideoView.objects.filter(completed=True).count()
        return round((completed_views / total_views) * 100, 1) if total_views > 0 else 0
