from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import connection
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, tenant_context

from core.models import Tenant
from .models import Asset, AssetReviewReminderLog


@shared_task
def send_asset_review_reminders():
    """
    Send asset review reminders seven days before review, on the review date and after overdue.
    """
    if connection.schema_name == get_public_schema_name():
        sent_count = 0
        tenant_results = {}
        for tenant in Tenant.objects.exclude(schema_name=get_public_schema_name()).iterator():
            with tenant_context(tenant):
                result = send_asset_review_reminders_for_current_tenant()
                tenant_results[tenant.schema_name] = result['sent']
                sent_count += result['sent']
        return {'sent': sent_count, 'tenants': tenant_results}

    return send_asset_review_reminders_for_current_tenant()


def send_asset_review_reminders_for_current_tenant():
    today = timezone.now().date()
    upcoming = today + timedelta(days=7)

    reminder_windows = [
        ('advance_warning', upcoming),
        ('due_today', today),
    ]
    sent_count = 0

    for reminder_type, review_date in reminder_windows:
        sent_count += send_reminders_for_date(reminder_type, review_date)

    overdue_assets = Asset.objects.filter(
        next_review_date__lt=today,
        owner__isnull=False,
        lifecycle_status__in=['active', 'maintenance'],
    ).select_related('owner')
    for asset in overdue_assets:
        sent_count += send_asset_reminder(asset, 'overdue', asset.next_review_date)

    return {'sent': sent_count}


def send_reminders_for_date(reminder_type, review_date):
    assets = Asset.objects.filter(
        next_review_date=review_date,
        owner__isnull=False,
        lifecycle_status__in=['active', 'maintenance'],
    ).select_related('owner')
    return sum(send_asset_reminder(asset, reminder_type, review_date) for asset in assets)


def send_asset_reminder(asset, reminder_type, review_date):
    if not asset.owner or not asset.owner.email:
        return 0

    log, created = AssetReviewReminderLog.objects.get_or_create(
        asset=asset,
        owner=asset.owner,
        reminder_type=reminder_type,
        review_date=review_date,
        defaults={'email_sent': False},
    )
    if not created and log.email_sent:
        return 0

    subject = f'Asset review {reminder_type.replace("_", " ")}: {asset.name}'
    message = (
        f'The asset {asset.asset_id} - {asset.name} has a review date of '
        f'{asset.next_review_date}. Please review and update the asset register.'
    )
    send_mail(
        subject,
        message,
        getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
        [asset.owner.email],
        fail_silently=False,
    )

    log.email_sent = True
    log.save(update_fields=['email_sent'])
    return 1
