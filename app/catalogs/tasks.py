from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
import logging

from .notifications import AssessmentReminderService
from .models import AssessmentReminderConfiguration

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def send_due_reminders(self):
    """
    Daily task to send assessment due date reminders to all users.
    This is the main scheduled task called by Celery Beat.
    
    Returns:
        dict: Summary of reminder processing results
    """
    try:
        logger.info("Starting daily assessment reminder processing")
        
        # Process all daily reminders
        results = AssessmentReminderService.process_daily_reminders()
        
        # Log summary
        total_sent = (
            results['advance_warnings_sent'] + 
            results['due_today_sent'] + 
            results['overdue_sent'] + 
            results['weekly_digests_sent']
        )
        
        logger.info(
            f"Daily reminder processing completed: "
            f"{total_sent} emails sent to {results['processed_users']} users. "
            f"Errors: {len(results['errors'])}"
        )
        
        # Log any errors
        for error in results['errors']:
            logger.error(f"Reminder processing error: {error}")
        
        return {
            'status': 'success',
            'total_emails_sent': total_sent,
            'users_processed': results['processed_users'],
            'advance_warnings': results['advance_warnings_sent'],
            'due_today': results['due_today_sent'],
            'overdue': results['overdue_sent'],
            'weekly_digests': results['weekly_digests_sent'],
            'errors': results['errors'],
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Critical error in send_due_reminders task: {str(e)}")
        
        # Retry the task if retries are available
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying reminder processing (attempt {self.request.retries + 1})")
            raise self.retry(exc=e)
        
        return {
            'status': 'error',
            'error_message': str(e),
            'timestamp': timezone.now().isoformat(),
            'retries_exhausted': True
        }


@shared_task
def send_immediate_reminder(assessment_id, user_id, reminder_type, days_before_due=None):
    """
    Send an immediate reminder for a specific assessment to a specific user.
    Used for ad-hoc reminders triggered by administrators or system events.
    
    Args:
        assessment_id (int): ID of the ControlAssessment
        user_id (int): ID of the User to send reminder to
        reminder_type (str): Type of reminder ('advance_warning', 'due_today', 'overdue')
        days_before_due (int, optional): Days before due date
    
    Returns:
        dict: Result of the reminder sending
    """
    try:
        from .models import ControlAssessment
        
        assessment = ControlAssessment.objects.get(id=assessment_id)
        user = User.objects.get(id=user_id)
        
        success = AssessmentReminderService.send_individual_reminder(
            assessment, user, reminder_type, days_before_due
        )
        
        logger.info(
            f"Immediate reminder sent for assessment {assessment.assessment_id} "
            f"to user {user.username}: {'success' if success else 'failed'}"
        )
        
        return {
            'status': 'success' if success else 'failed',
            'assessment_id': assessment_id,
            'user_id': user_id,
            'reminder_type': reminder_type,
            'email_sent': success,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error sending immediate reminder: {str(e)}")
        return {
            'status': 'error',
            'error_message': str(e),
            'assessment_id': assessment_id,
            'user_id': user_id,
            'timestamp': timezone.now().isoformat()
        }


@shared_task
def send_bulk_assessment_reminders(assessment_ids, reminder_type='due_today'):
    """
    Send reminders for multiple assessments to their assigned users.
    Useful for bulk operations triggered by administrators.
    
    Args:
        assessment_ids (list): List of ControlAssessment IDs
        reminder_type (str): Type of reminder to send
    
    Returns:
        dict: Summary of bulk reminder results
    """
    try:
        from .models import ControlAssessment
        
        assessments = ControlAssessment.objects.filter(
            id__in=assessment_ids,
            assigned_to__isnull=False
        ).select_related('assigned_to', 'control')
        
        results = {
            'total_assessments': assessments.count(),
            'emails_sent': 0,
            'emails_failed': 0,
            'errors': []
        }
        
        for assessment in assessments:
            if assessment.assigned_to:
                try:
                    days_before_due = assessment.days_until_due
                    success = AssessmentReminderService.send_individual_reminder(
                        assessment, assessment.assigned_to, reminder_type, days_before_due
                    )
                    
                    if success:
                        results['emails_sent'] += 1
                    else:
                        results['emails_failed'] += 1
                        
                except Exception as e:
                    error_msg = f"Failed to send reminder for assessment {assessment.id}: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
                    results['emails_failed'] += 1
        
        logger.info(
            f"Bulk reminder processing complete: "
            f"{results['emails_sent']} sent, {results['emails_failed']} failed"
        )
        
        return {
            'status': 'success',
            **results,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in bulk reminder processing: {str(e)}")
        return {
            'status': 'error',
            'error_message': str(e),
            'timestamp': timezone.now().isoformat()
        }


@shared_task
def cleanup_old_reminder_logs(days_old=90):
    """
    Clean up old reminder logs to prevent database bloat.
    
    Args:
        days_old (int): Delete logs older than this many days
    
    Returns:
        dict: Cleanup results
    """
    try:
        from datetime import timedelta
        from .models import AssessmentReminderLog
        
        cutoff_date = timezone.now() - timedelta(days=days_old)
        
        # Count logs to be deleted
        old_logs = AssessmentReminderLog.objects.filter(sent_at__lt=cutoff_date)
        count_to_delete = old_logs.count()
        
        # Delete old logs
        deleted_count, _ = old_logs.delete()
        
        logger.info(f"Cleaned up {deleted_count} reminder logs older than {days_old} days")
        
        return {
            'status': 'success',
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date.isoformat(),
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up reminder logs: {str(e)}")
        return {
            'status': 'error',
            'error_message': str(e),
            'timestamp': timezone.now().isoformat()
        }


@shared_task
def test_reminder_configuration(user_id):
    """
    Test reminder configuration for a specific user by sending a test email.
    Useful for testing notification settings.
    
    Args:
        user_id (int): ID of the User to test
    
    Returns:
        dict: Test results
    """
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        
        user = User.objects.get(id=user_id)
        config = AssessmentReminderConfiguration.get_or_create_for_user(user)
        
        if not config.enable_reminders or not config.email_notifications:
            return {
                'status': 'skipped',
                'reason': 'Reminders or email notifications disabled for user',
                'user_id': user_id,
                'timestamp': timezone.now().isoformat()
            }
        
        # Send test email
        subject = "Test Reminder - Assessment Notification System"
        message = f"""
Hello {user.get_full_name() or user.username},

This is a test email to verify that your assessment reminder notifications are working properly.

Your current reminder settings:
- Reminders enabled: {config.enable_reminders}
- Email notifications: {config.email_notifications}
- Advance warning days: {config.advance_warning_days}
- Weekly digest: {config.weekly_digest_enabled}

If you received this email, your notification system is working correctly!

Best regards,
Your Compliance Management System
        """.strip()
        
        success = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False
        )
        
        logger.info(f"Test reminder sent to user {user.username}: {'success' if success else 'failed'}")
        
        return {
            'status': 'success' if success else 'failed',
            'user_id': user_id,
            'email_sent': bool(success),
            'user_email': user.email,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error sending test reminder: {str(e)}")
        return {
            'status': 'error',
            'error_message': str(e),
            'user_id': user_id,
            'timestamp': timezone.now().isoformat()
        }