from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
import logging
from datetime import datetime, timedelta

from .models import (
    RiskAction,
    RiskActionReminderConfiguration,
    RiskActionReminderLog,
)
from .notifications import RiskActionReminderService

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_risk_action_due_reminders(self):
    """
    Daily task to send risk action reminders based on user configurations.
    Sends advance warnings, due today, and overdue notifications.
    """
    logger.info("Starting daily risk action reminder processing")
    
    try:
        total_processed = 0
        total_sent = 0
        
        # Get all users with risk actions assigned
        users_with_actions = User.objects.filter(
            assigned_risk_actions__isnull=False
        ).distinct()
        
        for user in users_with_actions:
            try:
                user_processed, user_sent = _process_user_reminders(user)
                total_processed += user_processed
                total_sent += user_sent
                
            except Exception as e:
                logger.error(f"Error processing reminders for user {user.username}: {str(e)}")
                continue
        
        logger.info(f"Risk action reminder processing complete: {total_processed} processed, {total_sent} sent")
        return {
            'status': 'success',
            'total_processed': total_processed,
            'total_sent': total_sent
        }
        
    except Exception as exc:
        logger.error(f"Error in send_risk_action_due_reminders: {str(exc)}")
        raise self.retry(exc=exc, countdown=300)


def _process_user_reminders(user):
    """
    Process reminders for a specific user.
    
    Returns:
        tuple: (processed_count, sent_count)
    """
    try:
        config = RiskActionReminderConfiguration.get_or_create_for_user(user)
        
        if not config.enable_reminders or not config.email_notifications:
            logger.debug(f"Reminders disabled for user {user.username}")
            return 0, 0
        
        # Get user's active risk actions
        actions = RiskAction.objects.filter(
            assigned_to=user,
            status__in=['pending', 'in_progress', 'deferred']
        )
        
        if config.silence_completed:
            actions = actions.exclude(status='completed')
        if config.silence_cancelled:
            actions = actions.exclude(status='cancelled')
        
        processed_count = 0
        sent_count = 0
        
        for action in actions:
            try:
                # Calculate days until due
                days_until_due = action.days_until_due
                
                # Send appropriate reminders
                if days_until_due < 0 and config.overdue_reminders:
                    # Overdue reminders
                    if _should_send_overdue_reminder(action, user, config):
                        if RiskActionReminderService.send_individual_reminder(
                            action, user, 'overdue', days_until_due
                        ):
                            sent_count += 1
                
                elif days_until_due == 0:
                    # Due today
                    if RiskActionReminderService.send_individual_reminder(
                        action, user, 'due_today', days_until_due
                    ):
                        sent_count += 1
                
                elif days_until_due > 0:
                    # Advance warnings based on user configuration
                    reminder_days = config.get_reminder_days()
                    if days_until_due in reminder_days:
                        if RiskActionReminderService.send_individual_reminder(
                            action, user, 'advance_warning', days_until_due
                        ):
                            sent_count += 1
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing reminder for action {action.action_id}: {str(e)}")
                continue
        
        logger.debug(f"User {user.username}: {processed_count} processed, {sent_count} sent")
        return processed_count, sent_count
        
    except Exception as e:
        logger.error(f"Error processing user reminders for {user.username}: {str(e)}")
        return 0, 0


def _should_send_overdue_reminder(action, user, config):
    """
    Determine if an overdue reminder should be sent based on frequency settings.
    """
    try:
        # Check when the last overdue reminder was sent
        last_overdue = RiskActionReminderLog.objects.filter(
            action=action,
            user=user,
            reminder_type='overdue',
            email_sent=True
        ).order_by('-sent_at').first()
        
        if not last_overdue:
            return True  # Never sent overdue reminder
        
        # Check frequency based on configuration
        if config.reminder_frequency == 'daily':
            # Send daily overdue reminders
            return last_overdue.sent_at.date() < timezone.now().date()
        elif config.reminder_frequency == 'weekly':
            # Send weekly overdue reminders
            return last_overdue.sent_at < timezone.now() - timedelta(days=7)
        else:  # custom
            # Use custom frequency for overdue (default to weekly if not specified)
            return last_overdue.sent_at < timezone.now() - timedelta(days=7)
    
    except Exception as e:
        logger.error(f"Error checking overdue reminder frequency: {str(e)}")
        return False


@shared_task(bind=True, max_retries=3)
def send_risk_action_weekly_digests(self):
    """
    Weekly task to send digest emails with summary of risk actions.
    """
    logger.info("Starting weekly risk action digest processing")
    
    try:
        total_sent = 0
        
        # Get all users with digest enabled
        users_with_digest = User.objects.filter(
            risk_action_reminder_config__weekly_digest_enabled=True,
            risk_action_reminder_config__email_notifications=True,
            assigned_risk_actions__isnull=False
        ).distinct()
        
        for user in users_with_digest:
            try:
                config = user.risk_action_reminder_config
                
                # Check if today matches the user's preferred digest day
                today_weekday = timezone.now().weekday()  # 0=Monday, 6=Sunday
                if today_weekday != config.weekly_digest_day:
                    continue
                
                # Get user's risk actions for digest
                actions = RiskAction.objects.filter(
                    Q(assigned_to=user) | Q(risk__risk_owner=user)
                ).filter(
                    status__in=['pending', 'in_progress', 'deferred']
                ).select_related('risk', 'assigned_to').order_by('due_date', '-priority')
                
                if actions.exists():
                    if RiskActionReminderService.send_weekly_digest(user, actions):
                        total_sent += 1
                        
            except Exception as e:
                logger.error(f"Error sending digest to user {user.username}: {str(e)}")
                continue
        
        logger.info(f"Weekly digest processing complete: {total_sent} digests sent")
        return {
            'status': 'success',
            'total_sent': total_sent
        }
        
    except Exception as exc:
        logger.error(f"Error in send_risk_action_weekly_digests: {str(exc)}")
        raise self.retry(exc=exc, countdown=300)


@shared_task
def send_immediate_risk_action_reminder(action_id, user_id, reminder_type='advance_warning'):
    """
    Send immediate reminder for a specific risk action.
    Used for admin-triggered notifications.
    
    Args:
        action_id: ID of the RiskAction
        user_id: ID of the User
        reminder_type: Type of reminder to send
    """
    try:
        action = RiskAction.objects.get(id=action_id)
        user = User.objects.get(id=user_id)
        
        days_until_due = action.days_until_due if hasattr(action, 'days_until_due') else None
        
        success = RiskActionReminderService.send_individual_reminder(
            action, user, reminder_type, days_until_due
        )
        
        logger.info(f"Immediate reminder sent for action {action.action_id} to {user.username}: {success}")
        return {'status': 'success', 'sent': success}
        
    except RiskAction.DoesNotExist:
        logger.error(f"RiskAction with id {action_id} does not exist")
        return {'status': 'error', 'message': 'Action not found'}
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} does not exist")
        return {'status': 'error', 'message': 'User not found'}
    except Exception as e:
        logger.error(f"Error sending immediate reminder: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def send_bulk_risk_action_reminders(action_ids, reminder_type='advance_warning'):
    """
    Send reminders for multiple risk actions in bulk.
    
    Args:
        action_ids: List of RiskAction IDs
        reminder_type: Type of reminder to send
    """
    try:
        sent_count = 0
        error_count = 0
        
        actions = RiskAction.objects.filter(id__in=action_ids).select_related('assigned_to', 'risk')
        
        for action in actions:
            try:
                if action.assigned_to:
                    days_until_due = action.days_until_due
                    
                    success = RiskActionReminderService.send_individual_reminder(
                        action, action.assigned_to, reminder_type, days_until_due
                    )
                    
                    if success:
                        sent_count += 1
                    else:
                        error_count += 1
                        
            except Exception as e:
                logger.error(f"Error sending bulk reminder for action {action.action_id}: {str(e)}")
                error_count += 1
                continue
        
        logger.info(f"Bulk reminder processing complete: {sent_count} sent, {error_count} errors")
        return {
            'status': 'success',
            'sent_count': sent_count,
            'error_count': error_count
        }
        
    except Exception as e:
        logger.error(f"Error in bulk reminder processing: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def cleanup_old_risk_action_reminder_logs(days_to_keep=90):
    """
    Clean up old reminder logs to prevent database bloat.
    
    Args:
        days_to_keep: Number of days of logs to keep (default 90)
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        
        deleted_count = RiskActionReminderLog.objects.filter(
            sent_at__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old risk action reminder logs")
        return {
            'status': 'success',
            'deleted_count': deleted_count
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up reminder logs: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def test_risk_action_reminder_configuration(user_id):
    """
    Test reminder configuration for a specific user by sending a test email.
    
    Args:
        user_id: ID of the User to test
    """
    try:
        user = User.objects.get(id=user_id)
        config = RiskActionReminderConfiguration.get_or_create_for_user(user)
        
        # Find a test action or create a mock one for testing
        test_action = RiskAction.objects.filter(assigned_to=user).first()
        
        if not test_action:
            # No actions found, just return config status
            return {
                'status': 'success',
                'message': f'Configuration loaded for {user.username}',
                'config': {
                    'enable_reminders': config.enable_reminders,
                    'email_notifications': config.email_notifications,
                    'advance_warning_days': config.advance_warning_days,
                    'reminder_frequency': config.reminder_frequency,
                    'weekly_digest_enabled': config.weekly_digest_enabled,
                }
            }
        
        # Send test reminder
        success = RiskActionReminderService.send_individual_reminder(
            test_action, user, 'advance_warning', 3  # 3 days before due
        )
        
        return {
            'status': 'success',
            'test_sent': success,
            'action_tested': test_action.action_id,
            'config': {
                'enable_reminders': config.enable_reminders,
                'email_notifications': config.email_notifications,
                'advance_warning_days': config.advance_warning_days,
                'reminder_frequency': config.reminder_frequency,
                'weekly_digest_enabled': config.weekly_digest_enabled,
            }
        }
        
    except User.DoesNotExist:
        return {'status': 'error', 'message': 'User not found'}
    except Exception as e:
        logger.error(f"Error testing reminder configuration: {str(e)}")
        return {'status': 'error', 'message': str(e)}