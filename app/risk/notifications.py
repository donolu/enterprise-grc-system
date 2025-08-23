from django.core.mail import send_mail, send_mass_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.db.models import Q
from django.contrib.auth import get_user_model
import logging
from datetime import datetime, timedelta

from .models import (
    RiskAction,
    RiskActionReminderConfiguration,
    RiskActionReminderLog,
    Risk
)

User = get_user_model()
logger = logging.getLogger(__name__)


class RiskActionReminderService:
    """
    Service for sending automated risk action reminders and notifications.
    Extends the existing reminder system pattern for risk actions.
    """
    
    @staticmethod
    def send_individual_reminder(action, user, reminder_type, days_before_due=None):
        """
        Send individual reminder for a specific risk action to a user.
        
        Args:
            action: RiskAction instance
            user: User instance
            reminder_type: Type of reminder ('advance_warning', 'due_today', 'overdue')
            days_before_due: Days before due date (negative for overdue)
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Get user's reminder configuration
            config = RiskActionReminderConfiguration.get_or_create_for_user(user)
            
            # Check if user wants reminders
            if not config.enable_reminders or not config.email_notifications:
                logger.debug(f"Risk action reminders disabled for user {user.username}")
                return False
            
            # Skip if action is in silenced status
            if config.silence_completed and action.status == 'completed':
                return False
            if config.silence_cancelled and action.status == 'cancelled':
                return False
            
            # Skip if already sent this reminder
            reminder_log_exists = RiskActionReminderLog.objects.filter(
                action=action,
                user=user,
                reminder_type=reminder_type,
                days_before_due=days_before_due
            ).exists()
            
            if reminder_log_exists:
                logger.debug(f"Reminder already sent: {reminder_type} for {action.action_id} to {user.username}")
                return False
            
            # Determine urgency level for styling
            urgency = RiskActionReminderService._determine_urgency(action, days_before_due)
            
            # Prepare email context
            context = {
                'user': user,
                'action': action,
                'risk': action.risk,
                'reminder_type': reminder_type,
                'days_before_due': days_before_due,
                'urgency': urgency,
                'site_domain': getattr(settings, 'SITE_DOMAIN', 'http://localhost:8000'),
                'action_url': f"{getattr(settings, 'SITE_DOMAIN', 'http://localhost:8000')}/admin/risk/riskaction/{action.pk}/change/",
                'risk_url': f"{getattr(settings, 'SITE_DOMAIN', 'http://localhost:8000')}/admin/risk/risk/{action.risk.pk}/change/",
            }
            
            # Generate subject based on reminder type
            subject = RiskActionReminderService._generate_subject(action, reminder_type, days_before_due)
            
            # Render email templates
            html_message = render_to_string('emails/risk_action_reminder.html', context)
            plain_message = render_to_string('emails/risk_action_reminder.txt', context)
            
            # Send email
            email_sent = send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            # Log the reminder
            RiskActionReminderLog.objects.create(
                action=action,
                user=user,
                reminder_type=reminder_type,
                subject=subject,
                email_sent=bool(email_sent),
                days_before_due=days_before_due
            )
            
            logger.info(f"Sent {reminder_type} reminder for {action.action_id} to {user.email}")
            return True
            
        except Exception as e:
            error_msg = f"Error sending reminder for {action.action_id} to {user.email}: {str(e)}"
            logger.error(error_msg)
            
            # Log failed attempt
            RiskActionReminderLog.objects.create(
                action=action,
                user=user,
                reminder_type=reminder_type,
                subject=f"Failed: {reminder_type}",
                email_sent=False,
                error_message=str(e),
                days_before_due=days_before_due
            )
            return False
    
    @staticmethod
    def send_weekly_digest(user, actions):
        """
        Send weekly digest of risk actions to user.
        
        Args:
            user: User instance
            actions: QuerySet of RiskAction instances
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            config = RiskActionReminderConfiguration.get_or_create_for_user(user)
            
            if not config.weekly_digest_enabled or not config.email_notifications:
                return False
            
            # Check if digest already sent this week
            week_start = timezone.now().date() - timedelta(days=7)
            digest_sent_this_week = RiskActionReminderLog.objects.filter(
                user=user,
                reminder_type='weekly_digest',
                sent_at__date__gte=week_start
            ).exists()
            
            if digest_sent_this_week:
                return False
            
            if not actions.exists():
                return False
            
            # Organize actions by status and priority
            context = {
                'user': user,
                'actions': actions,
                'overdue_actions': actions.filter(due_date__lt=timezone.now().date(), status__in=['pending', 'in_progress']),
                'due_soon_actions': actions.filter(
                    due_date__gte=timezone.now().date(),
                    due_date__lte=timezone.now().date() + timedelta(days=7),
                    status__in=['pending', 'in_progress']
                ),
                'in_progress_actions': actions.filter(status='in_progress'),
                'high_priority_actions': actions.filter(priority__in=['high', 'critical'], status__in=['pending', 'in_progress']),
                'site_domain': getattr(settings, 'SITE_DOMAIN', 'http://localhost:8000'),
                'week_ending': timezone.now().date(),
            }
            
            subject = f"Weekly Risk Action Digest - {timezone.now().strftime('%B %d, %Y')}"
            
            html_message = render_to_string('emails/risk_action_weekly_digest.html', context)
            plain_message = render_to_string('emails/risk_action_weekly_digest.txt', context)
            
            email_sent = send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            # Log the digest (use first action for logging purposes)
            if actions.exists():
                RiskActionReminderLog.objects.create(
                    action=actions.first(),
                    user=user,
                    reminder_type='weekly_digest',
                    subject=subject,
                    email_sent=bool(email_sent),
                )
            
            logger.info(f"Sent weekly digest to {user.email} with {actions.count()} actions")
            return True
            
        except Exception as e:
            logger.error(f"Error sending weekly digest to {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def send_assignment_notification(action, assigned_user, assigner=None):
        """
        Send notification when a risk action is assigned to a user.
        
        Args:
            action: RiskAction instance
            assigned_user: User instance who was assigned the action
            assigner: User instance who assigned the action (optional)
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            config = RiskActionReminderConfiguration.get_or_create_for_user(assigned_user)
            
            if not config.email_notifications:
                return False
            
            context = {
                'user': assigned_user,
                'action': action,
                'risk': action.risk,
                'assigner': assigner,
                'site_domain': getattr(settings, 'SITE_DOMAIN', 'http://localhost:8000'),
                'action_url': f"{getattr(settings, 'SITE_DOMAIN', 'http://localhost:8000')}/admin/risk/riskaction/{action.pk}/change/",
                'risk_url': f"{getattr(settings, 'SITE_DOMAIN', 'http://localhost:8000')}/admin/risk/risk/{action.risk.pk}/change/",
            }
            
            subject = f"Risk Action Assigned: {action.title} ({action.action_id})"
            
            html_message = render_to_string('emails/risk_action_assignment.html', context)
            plain_message = render_to_string('emails/risk_action_assignment.txt', context)
            
            email_sent = send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[assigned_user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            # Log the assignment notification
            RiskActionReminderLog.objects.create(
                action=action,
                user=assigned_user,
                reminder_type='assignment',
                subject=subject,
                email_sent=bool(email_sent),
            )
            
            logger.info(f"Sent assignment notification for {action.action_id} to {assigned_user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending assignment notification for {action.action_id}: {str(e)}")
            return False
    
    @staticmethod
    def _determine_urgency(action, days_before_due):
        """Determine urgency level based on action priority and days until due."""
        if days_before_due is not None and days_before_due < 0:
            return 'critical'  # Overdue
        elif action.priority == 'critical':
            return 'critical'
        elif action.priority == 'high' or (days_before_due is not None and days_before_due <= 1):
            return 'high'
        elif action.priority == 'medium' or (days_before_due is not None and days_before_due <= 3):
            return 'medium'
        else:
            return 'low'
    
    @staticmethod
    def _generate_subject(action, reminder_type, days_before_due):
        """Generate email subject based on reminder type and context."""
        if reminder_type == 'overdue':
            return f"⚠️ OVERDUE: Risk Action {action.action_id} - {action.title}"
        elif reminder_type == 'due_today':
            return f"📅 DUE TODAY: Risk Action {action.action_id} - {action.title}"
        elif reminder_type == 'advance_warning':
            if days_before_due == 1:
                return f"⏰ Due Tomorrow: Risk Action {action.action_id} - {action.title}"
            else:
                return f"📋 Due in {days_before_due} days: Risk Action {action.action_id} - {action.title}"
        else:
            return f"Risk Action Reminder: {action.action_id} - {action.title}"


class RiskActionNotificationService:
    """
    Service for immediate risk action notifications (not scheduled reminders).
    """
    
    @staticmethod
    def notify_status_change(action, old_status, new_status, changed_by=None):
        """
        Send notification when risk action status changes.
        
        Args:
            action: RiskAction instance
            old_status: Previous status
            new_status: New status
            changed_by: User who changed the status (optional)
        """
        try:
            # Notify assigned user if different from the person making the change
            if action.assigned_to and action.assigned_to != changed_by:
                config = RiskActionReminderConfiguration.get_or_create_for_user(action.assigned_to)
                
                if config.email_notifications:
                    context = {
                        'user': action.assigned_to,
                        'action': action,
                        'risk': action.risk,
                        'old_status': old_status,
                        'new_status': new_status,
                        'changed_by': changed_by,
                        'site_domain': getattr(settings, 'SITE_DOMAIN', 'http://localhost:8000'),
                        'action_url': f"{getattr(settings, 'SITE_DOMAIN', 'http://localhost:8000')}/admin/risk/riskaction/{action.pk}/change/",
                    }
                    
                    subject = f"Risk Action Status Update: {action.action_id} - Now {new_status.title()}"
                    
                    html_message = render_to_string('emails/risk_action_status_change.html', context)
                    plain_message = render_to_string('emails/risk_action_status_change.txt', context)
                    
                    send_mail(
                        subject=subject,
                        message=plain_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[action.assigned_to.email],
                        html_message=html_message,
                        fail_silently=True,
                    )
                    
                    logger.info(f"Sent status change notification for {action.action_id} to {action.assigned_to.email}")
            
            # Also notify risk owner if different from assigned user and changer
            if (action.risk.risk_owner and 
                action.risk.risk_owner != action.assigned_to and 
                action.risk.risk_owner != changed_by):
                
                context = {
                    'user': action.risk.risk_owner,
                    'action': action,
                    'risk': action.risk,
                    'old_status': old_status,
                    'new_status': new_status,
                    'changed_by': changed_by,
                    'site_domain': getattr(settings, 'SITE_DOMAIN', 'http://localhost:8000'),
                    'action_url': f"{getattr(settings, 'SITE_DOMAIN', 'http://localhost:8000')}/admin/risk/riskaction/{action.pk}/change/",
                }
                
                subject = f"Risk Action Status Update: {action.action_id} - Now {new_status.title()}"
                
                html_message = render_to_string('emails/risk_action_status_change.html', context)
                plain_message = render_to_string('emails/risk_action_status_change.txt', context)
                
                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[action.risk.risk_owner.email],
                    html_message=html_message,
                    fail_silently=True,
                )
                
                logger.info(f"Sent status change notification for {action.action_id} to risk owner {action.risk.risk_owner.email}")
                
        except Exception as e:
            logger.error(f"Error sending status change notification: {str(e)}")
    
    @staticmethod
    def notify_evidence_uploaded(evidence, uploader=None):
        """
        Send notification when evidence is uploaded for a risk action.
        
        Args:
            evidence: RiskActionEvidence instance
            uploader: User who uploaded the evidence (optional)
        """
        try:
            action = evidence.action
            
            # Notify assigned user if different from uploader
            if action.assigned_to and action.assigned_to != uploader:
                config = RiskActionReminderConfiguration.get_or_create_for_user(action.assigned_to)
                
                if config.email_notifications:
                    context = {
                        'user': action.assigned_to,
                        'action': action,
                        'risk': action.risk,
                        'evidence': evidence,
                        'uploader': uploader,
                        'site_domain': getattr(settings, 'SITE_DOMAIN', 'http://localhost:8000'),
                        'action_url': f"{getattr(settings, 'SITE_DOMAIN', 'http://localhost:8000')}/admin/risk/riskaction/{action.pk}/change/",
                    }
                    
                    subject = f"New Evidence Uploaded: {action.action_id} - {evidence.title}"
                    
                    html_message = render_to_string('emails/risk_action_evidence_uploaded.html', context)
                    plain_message = render_to_string('emails/risk_action_evidence_uploaded.txt', context)
                    
                    send_mail(
                        subject=subject,
                        message=plain_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[action.assigned_to.email],
                        html_message=html_message,
                        fail_silently=True,
                    )
                    
                    logger.info(f"Sent evidence upload notification for {action.action_id} to {action.assigned_to.email}")
                    
        except Exception as e:
            logger.error(f"Error sending evidence upload notification: {str(e)}")