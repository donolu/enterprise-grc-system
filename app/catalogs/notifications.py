from django.core.mail import send_mail, send_mass_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.db.models import Q
import logging
from datetime import datetime, timedelta

from .models import (
    ControlAssessment, 
    AssessmentReminderConfiguration, 
    AssessmentReminderLog
)

logger = logging.getLogger(__name__)


class AssessmentReminderService:
    """
    Service for sending automated assessment reminders and notifications.
    """
    
    @staticmethod
    def send_individual_reminder(assessment, user, reminder_type, days_before_due=None):
        """
        Send individual reminder for a specific assessment to a user.
        
        Args:
            assessment: ControlAssessment instance
            user: User instance
            reminder_type: Type of reminder ('advance_warning', 'due_today', 'overdue')
            days_before_due: Days before due date (negative for overdue)
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Get user's reminder configuration
            config = AssessmentReminderConfiguration.get_or_create_for_user(user)
            
            # Check if user wants reminders
            if not config.enable_reminders or not config.email_notifications:
                logger.debug(f"Reminders disabled for user {user.username}")
                return False
            
            # Skip if already sent this reminder
            reminder_log_exists = AssessmentReminderLog.objects.filter(
                assessment=assessment,
                user=user,
                reminder_type=reminder_type,
                days_before_due=days_before_due
            ).exists()
            
            if reminder_log_exists:
                logger.debug(f"Reminder already sent for {assessment.assessment_id} to {user.username}")
                return False
            
            # Skip completed or not applicable if configured
            if config.silence_completed_assessments and assessment.status == 'complete':
                return False
            if config.silence_not_applicable and assessment.status == 'not_applicable':
                return False
            
            # Prepare email context
            context = {
                'user': user,
                'assessment': assessment,
                'control': assessment.control,
                'framework': assessment.control.clause.framework,
                'reminder_type': reminder_type,
                'days_before_due': days_before_due,
                'is_overdue': assessment.is_overdue,
                'site_domain': settings.SITE_DOMAIN,
                'config': config,
            }
            
            # Calculate urgency and messaging
            urgency_class, urgency_message = AssessmentReminderService._get_urgency_info(
                assessment, reminder_type, days_before_due
            )
            context.update({
                'urgency_class': urgency_class,
                'urgency_message': urgency_message,
            })
            
            # Generate subject line
            subject = AssessmentReminderService._generate_subject_line(
                assessment, reminder_type, days_before_due
            )
            
            # Render email templates
            html_message = render_to_string(
                'catalogs/emails/assessment_reminder.html', 
                context
            )
            text_message = render_to_string(
                'catalogs/emails/assessment_reminder.txt', 
                context
            )
            
            # Send email
            success = send_mail(
                subject=subject,
                message=text_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False
            )
            
            # Log the reminder
            AssessmentReminderLog.objects.create(
                assessment=assessment,
                user=user,
                reminder_type=reminder_type,
                days_before_due=days_before_due,
                email_sent=bool(success)
            )
            
            logger.info(f"Sent {reminder_type} reminder for {assessment.assessment_id} to {user.email}")
            return bool(success)
            
        except Exception as e:
            logger.error(f"Failed to send reminder for {assessment.assessment_id} to {user.username}: {str(e)}")
            
            # Log failed attempt
            try:
                AssessmentReminderLog.objects.create(
                    assessment=assessment,
                    user=user,
                    reminder_type=reminder_type,
                    days_before_due=days_before_due,
                    email_sent=False
                )
            except:
                pass
            
            return False
    
    @staticmethod
    def send_weekly_digest(user):
        """
        Send weekly digest of upcoming and overdue assessments to a user.
        
        Args:
            user: User instance
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Get user's reminder configuration
            config = AssessmentReminderConfiguration.get_or_create_for_user(user)
            
            if not config.weekly_digest_enabled or not config.email_notifications:
                return False
            
            # Get assessments for this user
            upcoming_assessments = ControlAssessment.objects.filter(
                assigned_to=user,
                due_date__gte=timezone.now().date(),
                due_date__lte=timezone.now().date() + timedelta(days=14),
                status__in=['not_started', 'pending', 'in_progress', 'under_review']
            ).select_related('control', 'control__clause', 'control__clause__framework')
            
            overdue_assessments = ControlAssessment.objects.filter(
                assigned_to=user,
                due_date__lt=timezone.now().date(),
                status__in=['not_started', 'pending', 'in_progress', 'under_review']
            ).select_related('control', 'control__clause', 'control__clause__framework')
            
            # Skip if no assessments
            if not upcoming_assessments.exists() and not overdue_assessments.exists():
                return False
            
            # Check if digest already sent today
            today = timezone.now().date()
            digest_sent_today = AssessmentReminderLog.objects.filter(
                user=user,
                reminder_type='weekly_digest',
                sent_at__date=today
            ).exists()
            
            if digest_sent_today:
                return False
            
            # Prepare email context
            context = {
                'user': user,
                'upcoming_assessments': upcoming_assessments,
                'overdue_assessments': overdue_assessments,
                'config': config,
                'site_domain': settings.SITE_DOMAIN,
                'week_start': today,
                'week_end': today + timedelta(days=7),
            }
            
            # Generate subject line
            total_items = upcoming_assessments.count() + overdue_assessments.count()
            subject = f"Weekly Assessment Digest - {total_items} items require attention"
            
            # Render email templates
            html_message = render_to_string(
                'catalogs/emails/weekly_digest.html', 
                context
            )
            text_message = render_to_string(
                'catalogs/emails/weekly_digest.txt', 
                context
            )
            
            # Send email
            success = send_mail(
                subject=subject,
                message=text_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False
            )
            
            # Log the digest (using first assessment or create dummy log)
            sample_assessment = (upcoming_assessments.first() or 
                               overdue_assessments.first())
            
            if sample_assessment:
                AssessmentReminderLog.objects.create(
                    assessment=sample_assessment,
                    user=user,
                    reminder_type='weekly_digest',
                    email_sent=bool(success)
                )
            
            logger.info(f"Sent weekly digest to {user.email} with {total_items} assessments")
            return bool(success)
            
        except Exception as e:
            logger.error(f"Failed to send weekly digest to {user.username}: {str(e)}")
            return False
    
    @staticmethod
    def _get_urgency_info(assessment, reminder_type, days_before_due):
        """Get urgency class and message for reminder."""
        if reminder_type == 'overdue':
            days_overdue = abs(days_before_due) if days_before_due else 0
            if days_overdue > 7:
                return 'critical', f'CRITICAL: {days_overdue} days overdue'
            else:
                return 'high', f'OVERDUE: {days_overdue} days past due'
        elif reminder_type == 'due_today':
            return 'high', 'DUE TODAY'
        elif days_before_due and days_before_due <= 3:
            return 'medium', f'Due in {days_before_due} days'
        else:
            return 'low', f'Due in {days_before_due} days'
    
    @staticmethod
    def _generate_subject_line(assessment, reminder_type, days_before_due):
        """Generate email subject line based on reminder type."""
        control_id = assessment.control.control_id
        framework = assessment.control.clause.framework.short_name
        
        if reminder_type == 'overdue':
            days_overdue = abs(days_before_due) if days_before_due else 0
            return f"⚠️ OVERDUE: {control_id} ({framework}) - {days_overdue} days past due"
        elif reminder_type == 'due_today':
            return f"🚨 DUE TODAY: {control_id} ({framework}) assessment"
        elif reminder_type == 'advance_warning':
            return f"📅 Reminder: {control_id} ({framework}) due in {days_before_due} days"
        else:
            return f"📋 Assessment Reminder: {control_id} ({framework})"
    
    @staticmethod
    def process_daily_reminders():
        """
        Process all daily reminders for all users.
        This is the main function called by the Celery task.
        
        Returns:
            dict: Summary of reminder processing results
        """
        today = timezone.now().date()
        results = {
            'advance_warnings_sent': 0,
            'due_today_sent': 0,
            'overdue_sent': 0,
            'weekly_digests_sent': 0,
            'errors': [],
            'processed_users': 0,
        }
        
        logger.info("Starting daily reminder processing")
        
        try:
            # Get all users with active reminder configurations
            active_configs = AssessmentReminderConfiguration.objects.filter(
                enable_reminders=True,
                email_notifications=True
            ).select_related('user')
            
            for config in active_configs:
                user = config.user
                results['processed_users'] += 1
                
                try:
                    # Process individual assessment reminders
                    assessments = ControlAssessment.objects.filter(
                        assigned_to=user,
                        due_date__isnull=False,
                        status__in=['not_started', 'pending', 'in_progress', 'under_review']
                    ).select_related('control', 'control__clause', 'control__clause__framework')
                    
                    for assessment in assessments:
                        days_until_due = assessment.days_until_due
                        
                        if days_until_due is None:
                            continue
                        
                        # Send advance warning reminders
                        if days_until_due > 0 and days_until_due in config.get_reminder_days():
                            if AssessmentReminderService.send_individual_reminder(
                                assessment, user, 'advance_warning', days_until_due
                            ):
                                results['advance_warnings_sent'] += 1
                        
                        # Send due today reminders
                        elif days_until_due == 0:
                            if AssessmentReminderService.send_individual_reminder(
                                assessment, user, 'due_today', 0
                            ):
                                results['due_today_sent'] += 1
                        
                        # Send overdue reminders
                        elif days_until_due < 0 and config.overdue_reminders:
                            # Send overdue reminder based on frequency
                            should_send = False
                            if config.reminder_frequency == 'daily':
                                should_send = True
                            elif config.reminder_frequency == 'weekly':
                                should_send = (abs(days_until_due) % 7) == 0
                            
                            if should_send and AssessmentReminderService.send_individual_reminder(
                                assessment, user, 'overdue', days_until_due
                            ):
                                results['overdue_sent'] += 1
                    
                    # Send weekly digest if it's the configured day
                    if config.weekly_digest_enabled:
                        today_weekday = today.weekday()  # 0=Monday, 6=Sunday
                        if today_weekday == config.digest_day_of_week:
                            if AssessmentReminderService.send_weekly_digest(user):
                                results['weekly_digests_sent'] += 1
                
                except Exception as e:
                    error_msg = f"Error processing reminders for user {user.username}: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            total_sent = (results['advance_warnings_sent'] + results['due_today_sent'] + 
                         results['overdue_sent'] + results['weekly_digests_sent'])
            
            logger.info(f"Daily reminder processing complete: {total_sent} emails sent to {results['processed_users']} users")
            
        except Exception as e:
            error_msg = f"Critical error in daily reminder processing: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
        
        return results


class AssessmentNotificationService:
    """
    Service for sending immediate assessment-related notifications.
    """
    
    @staticmethod
    def send_assignment_notification(assessment, assigned_by=None):
        """
        Send notification when an assessment is assigned to a user.
        
        Args:
            assessment: ControlAssessment instance
            assigned_by: User who made the assignment (optional)
        
        Returns:
            bool: True if email sent successfully
        """
        if not assessment.assigned_to or not assessment.assigned_to.email:
            return False
        
        try:
            context = {
                'assessment': assessment,
                'control': assessment.control,
                'framework': assessment.control.clause.framework,
                'assigned_by': assigned_by,
                'site_domain': settings.SITE_DOMAIN,
            }
            
            subject = f"New Assessment Assignment: {assessment.control.control_id} ({assessment.control.clause.framework.short_name})"
            
            html_message = render_to_string(
                'catalogs/emails/assignment_notification.html', 
                context
            )
            text_message = render_to_string(
                'catalogs/emails/assignment_notification.txt', 
                context
            )
            
            success = send_mail(
                subject=subject,
                message=text_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[assessment.assigned_to.email],
                fail_silently=False
            )
            
            logger.info(f"Sent assignment notification for {assessment.assessment_id} to {assessment.assigned_to.email}")
            return bool(success)
            
        except Exception as e:
            logger.error(f"Failed to send assignment notification: {str(e)}")
            return False
    
    @staticmethod
    def send_status_change_notification(assessment, old_status, new_status, changed_by=None):
        """
        Send notification when assessment status changes.
        
        Args:
            assessment: ControlAssessment instance
            old_status: Previous status
            new_status: New status
            changed_by: User who changed the status (optional)
        
        Returns:
            bool: True if email sent successfully
        """
        # Only notify on significant status changes
        significant_changes = [
            ('not_started', 'in_progress'),
            ('in_progress', 'under_review'),
            ('under_review', 'complete'),
            ('in_progress', 'complete'),
        ]
        
        if (old_status, new_status) not in significant_changes:
            return False
        
        if not assessment.assigned_to or not assessment.assigned_to.email:
            return False
        
        try:
            context = {
                'assessment': assessment,
                'control': assessment.control,
                'framework': assessment.control.clause.framework,
                'old_status': old_status,
                'new_status': new_status,
                'changed_by': changed_by,
                'site_domain': settings.SITE_DOMAIN,
            }
            
            subject = f"Assessment Status Updated: {assessment.control.control_id} now {new_status.replace('_', ' ').title()}"
            
            html_message = render_to_string(
                'catalogs/emails/status_change_notification.html', 
                context
            )
            text_message = render_to_string(
                'catalogs/emails/status_change_notification.txt', 
                context
            )
            
            success = send_mail(
                subject=subject,
                message=text_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[assessment.assigned_to.email],
                fail_silently=False
            )
            
            logger.info(f"Sent status change notification for {assessment.assessment_id}")
            return bool(success)
            
        except Exception as e:
            logger.error(f"Failed to send status change notification: {str(e)}")
            return False