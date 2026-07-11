"""
Training Celery Tasks

Automated tasks for security awareness campaigns and training notifications.
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

from .models import SecurityAwarenessCampaign, CampaignDelivery, TrainingVideo

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task
def send_scheduled_awareness_campaigns():
    """
    Send security awareness campaigns that are due.
    Runs every hour to check for campaigns ready to send.
    """

    # Find campaigns due to send
    due_campaigns = SecurityAwarenessCampaign.objects.filter(
        is_active=True,
        next_send_date__lte=timezone.now()
    ).filter(
        # Only send if campaign hasn't ended
        models.Q(end_date__isnull=True) |
        models.Q(end_date__gt=timezone.now())
    )

    campaigns_sent = 0
    total_emails_sent = 0

    for campaign in due_campaigns:
        try:
            result = send_awareness_campaign(str(campaign.id))
            if result['success']:
                campaigns_sent += 1
                total_emails_sent += result['emails_sent']

                # Update next send date
                next_date = campaign.calculate_next_send_date()
                if next_date:
                    campaign.next_send_date = next_date
                    campaign.save(update_fields=['next_send_date'])
                else:
                    # End campaign if no more sends scheduled
                    campaign.is_active = False
                    campaign.save(update_fields=['is_active'])

        except Exception as e:
            logger.error(f"Failed to send campaign {campaign.id}: {e}")

    logger.info(f"Scheduled campaigns: {campaigns_sent} campaigns sent, {total_emails_sent} emails delivered")
    return {
        'campaigns_sent': campaigns_sent,
        'total_emails_sent': total_emails_sent
    }


@shared_task
def send_awareness_campaign(campaign_id):
    """
    Send a specific security awareness campaign.
    """
    from django.db import models

    try:
        campaign = SecurityAwarenessCampaign.objects.get(id=campaign_id)
    except SecurityAwarenessCampaign.DoesNotExist:
        logger.error(f"Campaign {campaign_id} not found")
        return {'success': False, 'error': 'Campaign not found'}

    if not campaign.is_active:
        logger.warning(f"Campaign {campaign_id} is not active")
        return {'success': False, 'error': 'Campaign is not active'}

    # Get target users
    if campaign.send_to_all_users:
        target_users = User.objects.filter(is_active=True)
    else:
        target_users = campaign.target_users.filter(is_active=True)

    if not target_users.exists():
        logger.warning(f"No target users found for campaign {campaign_id}")
        return {'success': False, 'error': 'No target users found'}

    emails_sent = 0
    emails_failed = 0

    for user in target_users:
        try:
            success = send_single_awareness_email(campaign, user)
            if success:
                emails_sent += 1
            else:
                emails_failed += 1

        except Exception as e:
            logger.error(f"Failed to send awareness email to {user.email}: {e}")
            emails_failed += 1

    # Update campaign statistics
    campaign.total_sent += emails_sent
    campaign.save(update_fields=['total_sent'])

    logger.info(f"Campaign {campaign.name}: {emails_sent} sent, {emails_failed} failed")
    return {
        'success': True,
        'emails_sent': emails_sent,
        'emails_failed': emails_failed
    }


@shared_task
def send_test_awareness_email(campaign_id, user_id):
    """
    Send a test awareness email to a specific user.
    """
    try:
        campaign = SecurityAwarenessCampaign.objects.get(id=campaign_id)
        user = User.objects.get(id=user_id)
    except (SecurityAwarenessCampaign.DoesNotExist, User.DoesNotExist) as e:
        logger.error(f"Test email failed: {e}")
        return {'success': False, 'error': str(e)}

    success = send_single_awareness_email(campaign, user, is_test=True)

    return {
        'success': success,
        'recipient': user.email,
        'campaign': campaign.name
    }


def send_single_awareness_email(campaign, user, is_test=False):
    """Send awareness email to a single user."""

    # Prepare email context
    context = {
        'user': user,
        'campaign': campaign,
        'unsubscribe_url': f"{settings.FRONTEND_URL}/training/unsubscribe/{user.id}",
        'training_url': f"{settings.FRONTEND_URL}/training",
        'is_test': is_test,
    }

    # Process email content with template variables
    try:
        from django.template import Context, Template
        email_template = Template(campaign.email_content)
        processed_content = email_template.render(Context(context))
    except Exception as e:
        logger.error(f"Failed to process email template: {e}")
        processed_content = campaign.email_content

    # Prepare email
    subject = f"[TEST] {campaign.subject_line}" if is_test else campaign.subject_line

    # Create HTML email with proper styling
    html_content = render_to_string('training/emails/awareness_campaign.html', {
        **context,
        'email_content': processed_content,
        'subject': subject
    })

    # Create text version
    text_content = render_to_string('training/emails/awareness_campaign.txt', {
        **context,
        'email_content': processed_content,
        'subject': subject
    })

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

        # Track delivery (skip for test emails)
        if not is_test:
            CampaignDelivery.objects.create(
                campaign=campaign,
                user=user,
                email_subject=subject,
                recipient_email=user.email,
                delivery_status='sent'
            )

        logger.info(f"Awareness email sent to {user.email} for campaign {campaign.name}")
        return True

    except Exception as e:
        logger.error(f"Failed to send awareness email to {user.email}: {e}")

        # Track failed delivery (skip for test emails)
        if not is_test:
            CampaignDelivery.objects.create(
                campaign=campaign,
                user=user,
                email_subject=subject,
                recipient_email=user.email,
                delivery_status='failed'
            )

        return False


@shared_task
def cleanup_old_campaign_deliveries():
    """
    Clean up old campaign delivery records.
    Runs weekly to remove delivery records older than 6 months.
    """

    cutoff_date = timezone.now() - timedelta(days=180)  # 6 months

    old_deliveries = CampaignDelivery.objects.filter(
        sent_at__lt=cutoff_date
    )

    deleted_count = old_deliveries.count()
    old_deliveries.delete()

    logger.info(f"Cleaned up {deleted_count} old campaign delivery records")
    return {'deleted_count': deleted_count}


@shared_task
def generate_training_analytics_report():
    """
    Generate weekly training analytics report.
    """
    from django.db.models import Count, Avg, Sum
    from .models import VideoView

    # Calculate analytics for the last week
    one_week_ago = timezone.now() - timedelta(days=7)

    # Video analytics
    videos = TrainingVideo.objects.filter(is_published=True)
    total_videos = videos.count()

    # Views in last week
    recent_views = VideoView.objects.filter(started_at__gte=one_week_ago)
    total_views_week = recent_views.count()
    unique_viewers_week = recent_views.values('user').distinct().count()
    avg_completion_week = recent_views.aggregate(
        avg=Avg('completion_percentage')
    )['avg'] or 0

    # Most watched videos
    most_watched = videos.annotate(
        weekly_views=Count('views', filter=models.Q(views__started_at__gte=one_week_ago))
    ).order_by('-weekly_views')[:5]

    # Campaign analytics
    campaigns = SecurityAwarenessCampaign.objects.filter(is_active=True)
    active_campaigns = campaigns.count()

    # Deliveries in last week
    recent_deliveries = CampaignDelivery.objects.filter(sent_at__gte=one_week_ago)
    emails_sent_week = recent_deliveries.count()
    emails_opened_week = recent_deliveries.filter(opened_at__isnull=False).count()
    emails_clicked_week = recent_deliveries.filter(clicked_at__isnull=False).count()

    # Calculate rates
    open_rate_week = (emails_opened_week / emails_sent_week * 100) if emails_sent_week > 0 else 0
    click_rate_week = (emails_clicked_week / emails_sent_week * 100) if emails_sent_week > 0 else 0

    # Prepare report data
    report_data = {
        'period': f"Week ending {timezone.now().strftime('%Y-%m-%d')}",
        'video_analytics': {
            'total_videos': total_videos,
            'total_views_week': total_views_week,
            'unique_viewers_week': unique_viewers_week,
            'avg_completion_rate': round(avg_completion_week, 1),
            'most_watched': [
                {
                    'title': video.title,
                    'weekly_views': video.weekly_views,
                    'category': video.category.name
                }
                for video in most_watched if video.weekly_views > 0
            ]
        },
        'campaign_analytics': {
            'active_campaigns': active_campaigns,
            'emails_sent_week': emails_sent_week,
            'open_rate_week': round(open_rate_week, 1),
            'click_rate_week': round(click_rate_week, 1)
        }
    }

    # Send report to admins
    send_training_analytics_report_email(report_data)

    logger.info(f"Weekly training analytics report generated")
    return report_data


def send_training_analytics_report_email(report_data):
    """Send weekly training analytics report to admins."""

    # Get admin recipients
    admin_users = User.objects.filter(is_superuser=True)
    recipients = [admin.email for admin in admin_users if admin.email]

    if not recipients:
        return False

    # Prepare email context
    context = {
        'report': report_data,
        'training_url': f"{settings.FRONTEND_URL}/training",
        'dashboard_url': f"{settings.FRONTEND_URL}/training/dashboard",
    }

    # Render email templates
    subject = f"Training Analytics Report - {report_data['period']}"

    text_content = render_to_string('training/emails/analytics_report.txt', context)
    html_content = render_to_string('training/emails/analytics_report.html', context)

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
        logger.info(f"Training analytics report sent to {len(recipients)} admins")
        return True
    except Exception as e:
        logger.error(f"Failed to send training analytics report: {e}")
        return False


@shared_task
def update_video_view_counts():
    """
    Update video view counts based on VideoView records.
    Runs daily to sync view counts.
    """

    from django.db.models import Count

    videos = TrainingVideo.objects.all()
    updated_count = 0

    for video in videos:
        actual_count = video.views.count()
        if video.view_count != actual_count:
            video.view_count = actual_count
            video.save(update_fields=['view_count'])
            updated_count += 1

    logger.info(f"Updated view counts for {updated_count} videos")
    return {'updated_count': updated_count}