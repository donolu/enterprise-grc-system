"""Catalogue and control-assessment service entry points."""

from datetime import timedelta

from django.db.models import Avg, Case, Count, FloatField, Q, Value, When
from django.utils import timezone

from .models import AssessmentEvidence, Control, ControlAssessment, Framework


ASSESSMENT_OPEN_STATUSES = ["not_started", "in_progress"]


def _maturity_score():
    return Case(
        When(assessments__maturity_level="ad_hoc", then=Value(1.0)),
        When(assessments__maturity_level="repeatable", then=Value(2.0)),
        When(assessments__maturity_level="defined", then=Value(3.0)),
        When(assessments__maturity_level="managed", then=Value(4.0)),
        When(assessments__maturity_level="optimized", then=Value(5.0)),
        output_field=FloatField(),
    )


def _effectiveness_score():
    return Case(
        When(effectiveness_rating="not_effective", then=Value(1.0)),
        When(effectiveness_rating="partially_effective", then=Value(2.0)),
        When(effectiveness_rating="largely_effective", then=Value(3.0)),
        When(effectiveness_rating="fully_effective", then=Value(4.0)),
        output_field=FloatField(),
    )


class CatalogueAnalyticsService:
    """Read-side analytics owned by the catalogue/control-assessment domain."""

    @staticmethod
    def executive_summary(now=None):
        today = now or timezone.now().date()
        return {
            "total_assessments": ControlAssessment.objects.count(),
            "active_assessments": ControlAssessment.objects.filter(
                status="in_progress"
            ).count(),
            "completed_assessments": ControlAssessment.objects.filter(
                status="complete"
            ).count(),
            "overdue_assessments": CatalogueAnalyticsService.overdue_assessment_count(today),
            "avg_completion_rate": ControlAssessment.objects.filter(
                status="complete"
            ).aggregate(avg_score=Avg("compliance_score"))["avg_score"]
            or 0,
        }

    @staticmethod
    def dashboard_data(now=None):
        today = now or timezone.now().date()
        six_months_ago = today - timedelta(days=180)

        framework_stats = list(
            Framework.objects.annotate(
                total_assessments=Count("control_assessments"),
                completed_assessments=Count(
                    "control_assessments",
                    filter=Q(control_assessments__status="complete"),
                ),
                in_progress_assessments=Count(
                    "control_assessments",
                    filter=Q(control_assessments__status="in_progress"),
                ),
                overdue_assessments=Count(
                    "control_assessments",
                    filter=Q(
                        control_assessments__due_date__lt=today,
                        control_assessments__status__in=ASSESSMENT_OPEN_STATUSES,
                    ),
                ),
                avg_score=Avg("control_assessments__compliance_score"),
            ).values(
                "name",
                "framework_type",
                "total_assessments",
                "completed_assessments",
                "in_progress_assessments",
                "overdue_assessments",
                "avg_score",
            )
        )

        for framework in framework_stats:
            total = framework["total_assessments"]
            framework["completion_rate"] = (
                round((framework["completed_assessments"] / total) * 100, 1)
                if total > 0
                else 0
            )

        control_effectiveness = list(
            Control.objects.annotate(
                assessment_count=Count("assessments"),
                avg_maturity=Avg(_maturity_score()),
                avg_effectiveness=Avg(_effectiveness_score()),
                high_risk_count=Count(
                    "assessments",
                    filter=Q(assessments__risk_rating__in=["high", "critical"]),
                ),
            )
            .values(
                "control_type",
                "automation_level",
                "assessment_count",
                "avg_maturity",
                "avg_effectiveness",
                "high_risk_count",
            )
            .order_by("-assessment_count")
        )

        assessment_trends = list(
            ControlAssessment.objects.filter(created_at__date__gte=six_months_ago)
            .extra(select={"month": "DATE_TRUNC('month', created_at)"})
            .values("month")
            .annotate(
                created=Count("id"),
                completed=Count("id", filter=Q(status="complete")),
                avg_score=Avg("compliance_score"),
            )
            .order_by("month")
        )

        evidence_stats = {
            "total_evidence": AssessmentEvidence.objects.count(),
            "validated_evidence": AssessmentEvidence.objects.filter(
                evidence__is_validated=True
            ).count(),
            "evidence_by_type": dict(
                AssessmentEvidence.objects.values("evidence__evidence_type")
                .annotate(count=Count("id"))
                .values_list("evidence__evidence_type", "count")
            ),
            "assessments_with_evidence": ControlAssessment.objects.filter(
                evidence_links__isnull=False
            )
            .distinct()
            .count(),
        }

        return {
            "framework_statistics": framework_stats,
            "control_effectiveness": control_effectiveness,
            "assessment_trends": assessment_trends,
            "evidence_statistics": evidence_stats,
            "overall_metrics": {
                "total_frameworks": Framework.objects.count(),
                "active_frameworks": Framework.objects.filter(status="active").count(),
                "total_controls": Control.objects.count(),
                "automated_controls": Control.objects.filter(
                    automation_level="automated"
                ).count(),
                "avg_maturity_score": Control.objects.aggregate(
                    avg=Avg(_maturity_score())
                )["avg"]
                or 0,
            },
            "generated_at": today.isoformat(),
        }

    @staticmethod
    def overdue_assessment_count(now=None):
        today = now or timezone.now().date()
        return ControlAssessment.objects.filter(
            due_date__lt=today,
            status__in=ASSESSMENT_OPEN_STATUSES,
        ).count()

    @staticmethod
    def compliance_gap_count():
        return ControlAssessment.objects.filter(
            status="complete",
            compliance_score__lt=70,
        ).count()

    @staticmethod
    def automation_rate_percentage():
        return Control.objects.filter(automation_level="automated").count() / max(
            Control.objects.count(), 1
        ) * 100

    @staticmethod
    def framework_risk_correlation(now=None):
        today = now or timezone.now().date()
        return list(
            Framework.objects.annotate(
                incomplete_assessments=Count(
                    "control_assessments",
                    filter=Q(
                        control_assessments__status__in=ASSESSMENT_OPEN_STATUSES,
                        control_assessments__due_date__lt=today,
                    ),
                ),
                low_scoring_assessments=Count(
                    "control_assessments",
                    filter=Q(
                        control_assessments__status="complete",
                        control_assessments__compliance_score__lt=70,
                    ),
                ),
            ).values(
                "name",
                "framework_type",
                "incomplete_assessments",
                "low_scoring_assessments",
            )
        )
