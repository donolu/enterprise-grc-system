"""Policy domain service entry points."""

from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from .models import Policy, PolicyAcknowledgment, PolicyDistribution, PolicyVersion


class PolicyAnalyticsService:
    """Read-side analytics owned by the policy domain."""

    @staticmethod
    def executive_summary():
        total_distributions = PolicyDistribution.objects.count()
        acknowledged_distributions = PolicyDistribution.objects.filter(
            acknowledged=True
        ).count()
        acknowledgment_rate = 0
        if total_distributions > 0:
            acknowledgment_rate = round(
                (acknowledged_distributions / total_distributions) * 100,
                1,
            )

        return {
            "total_policies": Policy.objects.count(),
            "active_policies": Policy.objects.filter(status="active").count(),
            "pending_acknowledgments": PolicyDistribution.objects.filter(
                acknowledged=False
            ).count(),
            "overdue_acknowledgments": PolicyAnalyticsService.overdue_acknowledgment_count(),
            "acknowledgment_rate": acknowledgment_rate,
        }

    @staticmethod
    def dashboard_data(now=None):
        today = now or timezone.now().date()
        ninety_days_ago = today - timedelta(days=90)

        policy_stats = {
            "total_policies": Policy.objects.count(),
            "active_policies": Policy.objects.filter(status="active").count(),
            "policies_requiring_acknowledgment": Policy.objects.filter(
                requires_acknowledgment=True
            ).count(),
            "draft_policies": Policy.objects.filter(status="draft").count(),
            "under_review_policies": Policy.objects.filter(
                status="under_review"
            ).count(),
        }

        total_distributions = PolicyDistribution.objects.count()
        acknowledged_distributions = PolicyDistribution.objects.filter(
            acknowledged=True
        ).count()

        acknowledgment_stats = {
            "total_distributions": total_distributions,
            "acknowledged_distributions": acknowledged_distributions,
            "pending_acknowledgments": total_distributions - acknowledged_distributions,
            "overdue_acknowledgments": PolicyAnalyticsService.overdue_acknowledgment_count(),
            "acknowledgment_rate": round(
                (acknowledged_distributions / max(total_distributions, 1)) * 100,
                1,
            ),
        }

        category_stats = list(
            Policy.objects.values("category", "category__name")
            .annotate(
                policy_count=Count("id"),
                active_policies=Count("id", filter=Q(status="active")),
                acknowledged_distributions=Count(
                    "versions__distributions",
                    filter=Q(versions__distributions__acknowledged=True),
                ),
                total_distributions=Count("versions__distributions"),
            )
            .order_by("-policy_count")
        )

        for category in category_stats:
            total = category["total_distributions"]
            category["avg_acknowledgment_rate"] = (
                round((category["acknowledged_distributions"] / total) * 100, 1)
                if total
                else 0
            )

        recent_activity = {
            "new_policies": Policy.objects.filter(
                created_at__date__gte=ninety_days_ago
            ).count(),
            "updated_policies": PolicyVersion.objects.filter(
                created_at__date__gte=ninety_days_ago
            ).count(),
            "new_acknowledgments": PolicyAcknowledgment.objects.filter(
                acknowledged_at__date__gte=ninety_days_ago
            ).count(),
            "distributions_sent": PolicyDistribution.objects.filter(
                distributed_at__date__gte=ninety_days_ago
            ).count(),
        }

        acknowledgment_trends = list(
            PolicyAcknowledgment.objects.filter(
                acknowledged_at__date__gte=today - timedelta(days=180)
            )
            .extra(select={"month": "DATE_TRUNC('month', acknowledged_at)"})
            .values("month")
            .annotate(acknowledgments=Count("id"))
            .order_by("month")
        )

        return {
            "policy_statistics": policy_stats,
            "acknowledgment_analytics": acknowledgment_stats,
            "category_breakdown": category_stats,
            "recent_activity": recent_activity,
            "acknowledgment_trends": acknowledgment_trends,
            "generated_at": today.isoformat(),
        }

    @staticmethod
    def overdue_acknowledgment_count():
        overdue_cutoff = timezone.now() - timedelta(days=30)
        return PolicyDistribution.objects.filter(
            acknowledged=False,
            distributed_at__lt=overdue_cutoff,
        ).count()

    @staticmethod
    def policy_violation_count():
        return PolicyAnalyticsService.overdue_acknowledgment_count()

    @staticmethod
    def acknowledgment_rate_percentage():
        total_distributions = PolicyDistribution.objects.count()
        acknowledged_distributions = PolicyDistribution.objects.filter(
            acknowledged=True
        ).count()
        return acknowledged_distributions / max(total_distributions, 1) * 100
