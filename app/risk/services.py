"""Risk domain service entry points."""

from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from .analytics import RiskAnalyticsService
from .models import Risk, RiskAction


OPEN_RISK_STATUSES = ["closed", "transferred"]
OPEN_ACTION_STATUSES = ["pending", "in_progress", "deferred"]


class RiskIntakeService:
    """Create risk records from structured intake data owned by another domain."""

    @staticmethod
    def create_vulnerability_risk(
        *,
        title,
        description,
        severity,
        risk_owner=None,
        created_by=None,
        next_review_date=None,
    ):
        impact, likelihood = _severity_to_risk_rating(severity)
        return Risk.objects.create(
            title=title,
            description=description,
            impact=impact,
            likelihood=likelihood,
            treatment_strategy="mitigate",
            status="identified",
            risk_owner=risk_owner,
            created_by=created_by,
            next_review_date=next_review_date,
        )

    @staticmethod
    def create_vulnerability_action(
        *,
        risk,
        title,
        remediation,
        severity,
        assigned_to=None,
        created_by=None,
        due_date=None,
    ):
        return RiskAction.objects.create(
            risk=risk,
            title=title,
            description=(
                remediation or "Remediate or document an accepted risk decision for this finding."
            ),
            action_type="technical",
            assigned_to=assigned_to,
            priority=_severity_to_priority(severity),
            due_date=due_date,
            created_by=created_by,
        )


class RiskCalendarProvider:
    """Provide risk-owned review and action due dates to calendar aggregation."""

    @staticmethod
    def list_events(event_factory, *, start_date=None, end_date=None, owner=None):
        review_queryset = (
            Risk.objects.filter(next_review_date__isnull=False)
            .exclude(status__in=["closed", "transferred"])
            .select_related("risk_owner")
        )
        action_queryset = RiskAction.objects.exclude(
            status__in=["completed", "cancelled"]
        ).select_related("assigned_to", "risk")

        if start_date:
            review_queryset = review_queryset.filter(next_review_date__gte=start_date)
            action_queryset = action_queryset.filter(due_date__gte=start_date)
        if end_date:
            review_queryset = review_queryset.filter(next_review_date__lte=end_date)
            action_queryset = action_queryset.filter(due_date__lte=end_date)
        if owner:
            review_queryset = review_queryset.filter(risk_owner=owner)
            action_queryset = action_queryset.filter(assigned_to=owner)

        return [
            *[
                event_factory(
                    source_type="risk_review",
                    source_id=str(risk.id),
                    title=f"Risk review due: {risk.title}",
                    due_date=risk.next_review_date,
                    owner=risk.risk_owner,
                    source_url=f"/api/risk/risks/{risk.id}/",
                    status=risk.status,
                    module="risk",
                    metadata={"risk_id": risk.risk_id, "risk_level": risk.risk_level},
                )
                for risk in review_queryset
            ],
            *[
                event_factory(
                    source_type="risk_action",
                    source_id=str(action.id),
                    title=f"Risk action due: {action.title}",
                    due_date=action.due_date,
                    owner=action.assigned_to,
                    source_url=f"/api/risk/actions/{action.id}/",
                    status=action.status,
                    module="risk",
                    metadata={"action_id": action.action_id, "risk_id": action.risk.risk_id},
                )
                for action in action_queryset
            ],
        ]


class RiskDomainAnalyticsService:
    """Read-side analytics owned by the risk domain."""

    @staticmethod
    def executive_summary(now=None):
        today = now or timezone.now().date()
        return {
            "total_risks": Risk.objects.count(),
            "active_risks": Risk.objects.exclude(status__in=OPEN_RISK_STATUSES).count(),
            "critical_high_risks": Risk.objects.filter(risk_level__in=["critical", "high"])
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
            "new_risks_30_days": Risk.objects.filter(created_at__date__gte=thirty_days_ago).count(),
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
            Risk.objects.values("category__name").annotate(count=Count("id")).order_by("-count")
        )


def _severity_to_risk_rating(severity):
    return {
        "critical": (5, 4),
        "high": (4, 4),
        "medium": (3, 3),
        "low": (2, 2),
        "info": (1, 1),
    }.get(severity, (2, 2))


def _severity_to_priority(severity):
    return {
        "critical": "critical",
        "high": "high",
        "medium": "medium",
        "low": "low",
        "info": "low",
    }.get(severity, "medium")
