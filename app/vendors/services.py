"""Vendor domain service entry points."""

from datetime import timedelta

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from .models import Vendor, VendorTask


OPEN_VENDOR_TASK_STATUSES = ["pending", "in_progress"]


class VendorCalendarProvider:
    """Provide vendor-owned contract and task dates to calendar aggregation."""

    @staticmethod
    def list_events(event_factory, *, start_date=None, end_date=None, owner=None):
        vendor_queryset = (
            Vendor.objects.filter(contract_end_date__isnull=False)
            .exclude(status__in=["terminated", "inactive"])
            .select_related("assigned_to")
        )
        task_queryset = VendorTask.objects.exclude(
            status__in=["completed", "cancelled"]
        ).select_related("assigned_to", "vendor")

        if start_date:
            vendor_queryset = vendor_queryset.filter(contract_end_date__gte=start_date)
            task_queryset = task_queryset.filter(due_date__gte=start_date)
        if end_date:
            vendor_queryset = vendor_queryset.filter(contract_end_date__lte=end_date)
            task_queryset = task_queryset.filter(due_date__lte=end_date)
        if owner:
            vendor_queryset = vendor_queryset.filter(assigned_to=owner)
            task_queryset = task_queryset.filter(assigned_to=owner)

        return [
            *[
                event_factory(
                    source_type="vendor_contract",
                    source_id=str(vendor.id),
                    title=f"Vendor contract expires: {vendor.name}",
                    due_date=vendor.contract_end_date,
                    owner=vendor.assigned_to,
                    source_url=f"/api/vendors/vendors/{vendor.id}/",
                    status=vendor.status,
                    module="vendors",
                    metadata={"vendor_id": vendor.vendor_id},
                )
                for vendor in vendor_queryset
            ],
            *[
                event_factory(
                    source_type="vendor_task",
                    source_id=str(task.id),
                    title=f"Vendor task due: {task.title}",
                    due_date=task.due_date,
                    owner=task.assigned_to,
                    source_url=f"/api/vendors/tasks/{task.id}/",
                    status=task.status,
                    module="vendors",
                    metadata={"task_id": task.task_id, "vendor_id": task.vendor.vendor_id},
                )
                for task in task_queryset
            ],
        ]


class VendorAnalyticsService:
    """Read-side analytics owned by the vendor domain."""

    @staticmethod
    def executive_summary(now=None):
        today = now or timezone.now().date()
        return {
            "total_vendors": Vendor.objects.count(),
            "active_vendors": Vendor.objects.filter(status="active").count(),
            "high_risk_vendors": Vendor.objects.filter(risk_level="high").count(),
            "contracts_expiring_soon": Vendor.objects.filter(
                contract_end_date__lte=today + timedelta(days=90),
                contract_end_date__gte=today,
                status="active",
            ).count(),
            "overdue_tasks": VendorAnalyticsService.overdue_task_count(today),
        }

    @staticmethod
    def dashboard_data(now=None):
        today = now or timezone.now().date()
        vendor_risk_stats = {
            "risk_distribution": dict(
                Vendor.objects.values("risk_level")
                .annotate(count=Count("id"))
                .values_list("risk_level", "count")
            ),
            "total_vendors": Vendor.objects.count(),
            "active_vendors": Vendor.objects.filter(status="active").count(),
            "total_annual_spend": Vendor.objects.aggregate(total=Sum("annual_spend"))["total"] or 0,
            "avg_performance_score": Vendor.objects.aggregate(avg=Avg("performance_score"))["avg"]
            or 0,
        }

        contract_metrics = {
            "expiring_30_days": Vendor.objects.filter(
                contract_end_date__lte=today + timedelta(days=30),
                contract_end_date__gte=today,
                status="active",
            ).count(),
            "expiring_90_days": Vendor.objects.filter(
                contract_end_date__lte=today + timedelta(days=90),
                contract_end_date__gte=today,
                status="active",
            ).count(),
            "expired_contracts": Vendor.objects.filter(
                contract_end_date__lt=today,
                status="active",
            ).count(),
            "renewals_needed": Vendor.objects.filter(
                contract_end_date__lte=today + timedelta(days=180),
                contract_end_date__gte=today,
                status="active",
            ).count(),
        }

        task_analytics = {
            "total_tasks": VendorTask.objects.count(),
            "overdue_tasks": VendorAnalyticsService.overdue_task_count(today),
            "due_this_week": VendorTask.objects.filter(
                due_date__gte=today,
                due_date__lte=today + timedelta(days=7),
                status__in=OPEN_VENDOR_TASK_STATUSES,
            ).count(),
            "task_type_distribution": dict(
                VendorTask.objects.values("task_type")
                .annotate(count=Count("id"))
                .values_list("task_type", "count")
            ),
            "completion_rate": VendorAnalyticsService.task_completion_rate(),
        }

        top_vendors = list(
            Vendor.objects.values(
                "name",
                "risk_level",
                "annual_spend",
                "performance_score",
                "contract_end_date",
                "status",
            ).order_by("-annual_spend")[:10]
        )

        high_risk_vendors = list(
            Vendor.objects.filter(risk_level="high")
            .values("name", "annual_spend", "performance_score", "contract_end_date")
            .annotate(
                open_tasks=Count(
                    "tasks",
                    filter=Q(tasks__status__in=OPEN_VENDOR_TASK_STATUSES),
                )
            )
            .order_by("-annual_spend")
        )

        return {
            "vendor_risk_statistics": vendor_risk_stats,
            "contract_management": contract_metrics,
            "task_analytics": task_analytics,
            "top_vendors": top_vendors,
            "high_risk_vendors": high_risk_vendors,
            "generated_at": today.isoformat(),
        }

    @staticmethod
    def overdue_task_count(now=None):
        today = now or timezone.now().date()
        return VendorTask.objects.filter(
            due_date__lt=today,
            status__in=OPEN_VENDOR_TASK_STATUSES,
        ).count()

    @staticmethod
    def high_or_critical_vendor_count():
        return Vendor.objects.filter(risk_level__in=["high", "critical"]).count()

    @staticmethod
    def high_risk_assessment_correlation():
        return list(
            Vendor.objects.filter(risk_level="high")
            .values("name", "annual_spend")
            .annotate(
                assessment_count=Count(
                    "services",
                    filter=Q(services__risk_assessment_completed=True),
                )
            )
        )

    @staticmethod
    def task_completion_rate():
        total_tasks = VendorTask.objects.count()
        completed_tasks = VendorTask.objects.filter(status="completed").count()
        return round((completed_tasks / total_tasks) * 100, 1) if total_tasks > 0 else 0

    @staticmethod
    def assessment_coverage_percentage():
        return (
            Vendor.objects.filter(services__risk_assessment_completed=True).distinct().count()
            / max(Vendor.objects.count(), 1)
            * 100
        )
