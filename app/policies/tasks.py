"""
Policy Repository Celery Tasks

Automated tasks for policy acknowledgment reminders and notifications.
"""

from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.db import models
from datetime import timedelta
import logging

from .models import PolicyDistribution, PolicyAcknowledgment

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task
def send_policy_acknowledgment_reminders():
    """
    Send reminders to users who haven't acknowledged policies.
    Runs daily to check for policies requiring reminders.
    """

    # Find distributions that need reminders
    # Criteria:
    # - Not acknowledged
    # - Distributed more than 7 days ago
    # - No reminder sent in the last 7 days OR never sent a reminder

    reminder_date = timezone.now() - timedelta(days=7)

    distributions_needing_reminders = PolicyDistribution.objects.filter(
        acknowledged=False,
        distributed_at__lte=reminder_date
    ).filter(
        # Either never sent a reminder or last reminder was over 7 days ago
        models.Q(last_reminder_sent__isnull=True) |
        models.Q(last_reminder_sent__lte=reminder_date)
    ).select_related(
        'policy_version__policy__category',
        'distributed_to',
        'distributed_by'
    )[:50]  # Limit batch size

    reminders_sent = 0

    for distribution in distributions_needing_reminders:
        try:
            success = send_single_acknowledgment_reminder(distribution)
            if success:
                reminders_sent += 1

                # Update reminder tracking
                distribution.reminder_count += 1
                distribution.last_reminder_sent = timezone.now()
                distribution.save(update_fields=['reminder_count', 'last_reminder_sent'])

        except Exception as e:
            logger.error(f"Failed to send reminder for distribution {distribution.id}: {e}")

    logger.info(f"Policy acknowledgment reminders: {reminders_sent} reminders sent")
    return {
        'reminders_sent': reminders_sent,
        'total_checked': distributions_needing_reminders.count()
    }


@shared_task
def send_overdue_policy_notifications():
    """
    Send notifications for overdue policy acknowledgments.
    Runs weekly to notify managers about overdue acknowledgments.
    """

    # Find distributions overdue by more than 30 days
    overdue_date = timezone.now() - timedelta(days=30)

    overdue_distributions = PolicyDistribution.objects.filter(
        acknowledged=False,
        distributed_at__lte=overdue_date
    ).select_related(
        'policy_version__policy__category',
        'distributed_to',
        'distributed_by'
    )

    if not overdue_distributions.exists():
        logger.info("No overdue policy acknowledgments found")
        return {'overdue_count': 0}

    # Group by policy and send summary emails to policy owners and admins
    policies_with_overdue = {}

    for distribution in overdue_distributions:
        policy = distribution.policy_version.policy
        policy_id = policy.id

        if policy_id not in policies_with_overdue:
            policies_with_overdue[policy_id] = {
                'policy': policy,
                'overdue_users': []
            }

        days_overdue = (timezone.now() - distribution.distributed_at).days
        policies_with_overdue[policy_id]['overdue_users'].append({
            'user': distribution.distributed_to,
            'distributed_at': distribution.distributed_at,
            'days_overdue': days_overdue,
            'reminder_count': distribution.reminder_count
        })

    # Send notifications to policy owners and admins
    notifications_sent = 0
    for policy_data in policies_with_overdue.values():
        try:
            success = send_overdue_policy_notification(policy_data)
            if success:
                notifications_sent += 1
        except Exception as e:
            logger.error(f"Failed to send overdue notification for policy {policy_data['policy'].id}: {e}")

    logger.info(f"Overdue policy notifications: {notifications_sent} notifications sent")
    return {
        'notifications_sent': notifications_sent,
        'policies_with_overdue': len(policies_with_overdue)
    }


@shared_task
def generate_acknowledgment_report():
    """
    Generate weekly acknowledgment status report.
    """
    from django.db.models import Count, Q

    # Calculate overall stats
    total_active_policies = PolicyDistribution.objects.filter(
        policy_version__is_active=True
    ).values('policy_version__policy').distinct().count()

    total_distributions = PolicyDistribution.objects.filter(
        policy_version__is_active=True
    ).count()

    total_acknowledgments = PolicyDistribution.objects.filter(
        policy_version__is_active=True,
        acknowledged=True
    ).count()

    overall_rate = (
        (total_acknowledgments / total_distributions * 100)
        if total_distributions > 0 else 0.0
    )

    # Get policies with low acknowledgment rates
    low_rate_policies = []

    from .models import Policy
    for policy in Policy.objects.filter(versions__is_active=True):
        current_version = policy.current_version
        if not current_version:
            continue

        distributions = PolicyDistribution.objects.filter(policy_version=current_version)
        total = distributions.count()
        acknowledged = distributions.filter(acknowledged=True).count()

        rate = (acknowledged / total * 100) if total > 0 else 0.0

        if rate < 70 and total > 0:  # Policies with less than 70% acknowledgment rate
            low_rate_policies.append({
                'policy': policy,
                'total_distributed': total,
                'acknowledged': acknowledged,
                'rate': round(rate, 1)
            })

    # Sort by rate (lowest first)
    low_rate_policies.sort(key=lambda x: x['rate'])

    report_data = {
        'period': f"Week ending {timezone.now().strftime('%Y-%m-%d')}",
        'overall_stats': {
            'total_active_policies': total_active_policies,
            'total_distributions': total_distributions,
            'total_acknowledgments': total_acknowledgments,
            'overall_rate': round(overall_rate, 1)
        },
        'low_rate_policies': low_rate_policies[:10]  # Top 10 policies needing attention
    }

    # Send report to admins
    send_acknowledgment_report_email(report_data)

    logger.info(f"Weekly acknowledgment report generated: {overall_rate}% overall rate")
    return report_data


def send_single_acknowledgment_reminder(distribution):
    """Send acknowledgment reminder to a single user."""

    policy = distribution.policy_version.policy
    version = distribution.policy_version
    user = distribution.distributed_to

    # Prepare email context
    context = {
        'user': user,
        'policy': policy,
        'version': version,
        'distribution': distribution,
        'days_since_distribution': (timezone.now() - distribution.distributed_at).days,
        'acknowledge_url': f"{settings.FRONTEND_URL}/policies/{policy.id}/acknowledge",
        'policy_url': f"{settings.FRONTEND_URL}/policies/{policy.id}",
    }

    # Render email templates
    subject = f"Reminder: Please acknowledge policy - {policy.title}"

    text_content = render_to_string('policies/emails/acknowledgment_reminder.txt', context)
    html_content = render_to_string('policies/emails/acknowledgment_reminder.html', context)

    # Send email
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email]
    )
    email.attach_alternative(html_content, "text/html")

    try:
        email.send()
        logger.info(f"Acknowledgment reminder sent to {user.email} for policy {policy.policy_code}")
        return True
    except Exception as e:
        logger.error(f"Failed to send acknowledgment reminder to {user.email}: {e}")
        return False


def send_overdue_policy_notification(policy_data):
    """Send overdue notification to policy owner and admins."""

    policy = policy_data['policy']
    overdue_users = policy_data['overdue_users']

    # Get recipients: policy owner + superusers
    recipients = []
    if policy.owner and policy.owner.email:
        recipients.append(policy.owner.email)

    # Add superusers as recipients
    admin_users = User.objects.filter(is_superuser=True)
    for admin in admin_users:
        if admin.email and admin.email not in recipients:
            recipients.append(admin.email)

    if not recipients:
        return False

    # Prepare email context
    context = {
        'policy': policy,
        'overdue_users': overdue_users,
        'total_overdue': len(overdue_users),
        'policy_url': f"{settings.FRONTEND_URL}/admin/policies/policy/{policy.id}/change/",
        'dashboard_url': f"{settings.FRONTEND_URL}/policies/dashboard",
    }

    # Render email templates
    subject = f"Policy Overdue Alert: {policy.title} - {len(overdue_users)} users overdue"

    text_content = render_to_string('policies/emails/overdue_notification.txt', context)
    html_content = render_to_string('policies/emails/overdue_notification.html', context)

    # Send email
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients
    )
    email.attach_alternative(html_content, "text/html")

    try:
        email.send()
        logger.info(f"Overdue policy notification sent for {policy.policy_code} to {len(recipients)} recipients")
        return True
    except Exception as e:
        logger.error(f"Failed to send overdue notification for policy {policy.policy_code}: {e}")
        return False


def send_acknowledgment_report_email(report_data):
    """Send weekly acknowledgment report to admins."""

    # Get admin recipients
    admin_users = User.objects.filter(is_superuser=True)
    recipients = [admin.email for admin in admin_users if admin.email]

    if not recipients:
        return False

    # Prepare email context
    context = {
        'report': report_data,
        'dashboard_url': f"{settings.FRONTEND_URL}/policies/dashboard",
    }

    # Render email templates
    subject = f"Policy Acknowledgment Report - {report_data['period']}"

    text_content = render_to_string('policies/emails/weekly_report.txt', context)
    html_content = render_to_string('policies/emails/weekly_report.html', context)

    # Send email
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients
    )
    email.attach_alternative(html_content, "text/html")

    try:
        email.send()
        logger.info(f"Weekly acknowledgment report sent to {len(recipients)} admins")
        return True
    except Exception as e:
        logger.error(f"Failed to send weekly acknowledgment report: {e}")
        return False


@shared_task
def cleanup_expired_acknowledgments():
    """
    Clean up expired acknowledgments and mark policies for re-acknowledgment.
    Runs daily to check for expired acknowledgments.
    """

    expired_acknowledgments = PolicyAcknowledgment.objects.filter(
        expires_at__lt=timezone.now()
    ).select_related('policy_version__policy', 'user')

    cleaned_count = 0
    redistributed_count = 0

    for ack in expired_acknowledgments:
        try:
            policy_version = ack.policy_version
            user = ack.user

            # Create new distribution for re-acknowledgment if policy is still active
            if policy_version.is_active:
                distribution, created = PolicyDistribution.objects.get_or_create(
                    policy_version=policy_version,
                    distributed_to=user,
                    defaults={
                        'distributed_by': policy_version.policy.owner,
                        'notification_sent': False,
                        'acknowledged': False
                    }
                )

                if created:
                    redistributed_count += 1
                    logger.info(f"Re-distributed policy {policy_version.policy.policy_code} to {user.email} due to expired acknowledgment")

            # Delete expired acknowledgment
            ack.delete()
            cleaned_count += 1

        except Exception as e:
            logger.error(f"Failed to cleanup expired acknowledgment {ack.id}: {e}")

    logger.info(f"Cleaned up {cleaned_count} expired acknowledgments, redistributed {redistributed_count} policies")
    return {
        'cleaned_count': cleaned_count,
        'redistributed_count': redistributed_count
    }