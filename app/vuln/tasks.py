from celery import shared_task
from django_tenants.utils import schema_context, tenant_context

from core.models import Tenant

from .models import ScanSchedule
from .services import advance_schedule_after_queue, create_scan_job, execute_scan_job


@shared_task
def run_scan_job(job_id, schema_name=None):
    if not schema_name:
        return execute_scan_job(job_id)

    with schema_context('public'):
        tenant = Tenant.objects.get(schema_name=schema_name)

    with tenant_context(tenant):
        return execute_scan_job(job_id)


@shared_task
def run_due_scan_schedules():
    from django.utils import timezone

    totals = {'queued': 0, 'tenants': {}}
    with schema_context('public'):
        tenants = list(Tenant.objects.exclude(schema_name='public'))

    for tenant in tenants:
        with tenant_context(tenant):
            due_schedules = ScanSchedule.objects.select_related('target').filter(
                is_active=True,
                next_run_at__lte=timezone.now(),
                target__status='approved',
            )
            queued = 0
            for schedule in due_schedules:
                job = create_scan_job(schedule.target, schedule=schedule)
                advance_schedule_after_queue(schedule)
                run_scan_job.delay(str(job.id), tenant.schema_name)
                queued += 1
            totals['tenants'][tenant.schema_name] = {'queued': queued}
            totals['queued'] += queued
    return totals
