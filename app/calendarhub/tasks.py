from celery import shared_task
from django_tenants.utils import schema_context, tenant_context

from core.models import Tenant

from .services import send_due_reminders


@shared_task
def send_calendar_deadline_reminders():
    results = {}
    total_sent = 0
    total_skipped = 0
    total_checked = 0

    with schema_context('public'):
        tenants = list(Tenant.objects.exclude(schema_name='public'))

    for tenant in tenants:
        with tenant_context(tenant):
            tenant_result = send_due_reminders()
        results[tenant.schema_name] = tenant_result
        total_sent += tenant_result['sent']
        total_skipped += tenant_result['skipped']
        total_checked += tenant_result['checked']

    return {
        'tenants': results,
        'sent': total_sent,
        'skipped': total_skipped,
        'checked': total_checked,
    }
