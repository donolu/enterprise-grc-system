"""Risk domain service entry points."""

from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from .analytics import RiskAnalyticsService
from .models import Risk, RiskAction


OPEN_RISK_STATUSES = ["closed", "transferred"]
OPEN_ACTION_STATUSES = ["pending", "in_progress", "deferred"]


class RiskDomainAnalyticsService:
    """Read-side analytics owned by the risk domain."""

    @staticmethod
    def executive_summary(now=None):
        today = now or timezone.now().date()
        return {
            "total_risks": Risk.objects.count(),
            "active_risks": Risk.objects.exclude(status__in=OPEN_RISK_STATUSES).count(),
            "critical_high_risks": Risk.objects.filter(
                risk_level__in=["critical", "high"]
            )
            .exclude(status__in=OPEN_RISK_STATUSES)
            .count(),
            "overdue_actions": RiskAction.objects.filter(
                due_date__lt=today,
                status__in=OPEN_ACTION_STATUSES,
            ).count(),
        }

    @staticmethod
    def active_risk_count():
        return Risk.objects.exclude(status__in=OPEN_RISK_STATUSES).count()

    @staticmethod
    def velocity_metrics(now=None):
        today = now or timezone.now().date()
        thirty_days_ago = today - timedelta(days=30)
        return {
            "new_risks_30_days": Risk.objects.filter(
                created_at__date__gte=thirty_days_ago
            ).count(),
            "resolved_risks_30_days": Risk.objects.filter(
                closed_date__gte=thirty_days_ago,
                closed_date__isnull=False,
            ).count(),
            "escalated_risks": Risk.objects.filter(
                created_at__date__gte=thirty_days_ago,
                risk_level__in=["high", "critical"],
            ).count(),
            "overdue_actions": RiskAction.objects.filter(
                due_date__lt=today,
                status__in=["pending", "in_progress"],
            ).count(),
        }

    @staticmethod
    def treatment_coverage_percentage():
        total_risks = Risk.objects.count()
        covered_risks = (
            Risk.objects.exclude(treatment_strategy__isnull=True)
            .exclude(treatment_strategy="")
            .count()
        )
        return covered_risks / max(total_risks, 1) * 100

    @staticmethod
    def overview_stats():
        return RiskAnalyticsService.get_risk_overview_stats()

    @staticmethod
    def category_breakdown():
        return list(
            Risk.objects.values("category__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
