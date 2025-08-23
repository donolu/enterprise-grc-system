"""
Vendor Task Notification System

Handles automated email reminders for vendor-related tasks including contract renewals,
security reviews, compliance assessments, and other vendor activities.
"""

from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class VendorTaskNotificationService:
    """
    Service for sending vendor task-related email notifications.
    Handles reminder emails, escalations, and task completion notifications.
    """
    
    def __init__(self):
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@aximcyber.com')
        self.site_name = getattr(settings, 'SITE_NAME', 'AxiMCyber GRC Platform')
    
    def send_task_reminder(self, task, recipient_email: str = None) -> bool:
        """
        Send reminder email for a specific vendor task.
        
        Args:
            task: VendorTask instance
            recipient_email: Optional specific email address (defaults to assigned user)
            
        Returns:
            bool: True if email was sent successfully
        """
        try:
            # Determine recipient
            if recipient_email:
                recipient = recipient_email
                recipient_name = "Team Member"
            elif task.assigned_to:
                recipient = task.assigned_to.email
                recipient_name = task.assigned_to.get_full_name() or task.assigned_to.username
            else:
                logger.warning(f"No recipient for task reminder: {task.task_id}")
                return False
            
            # Prepare email context
            context = {
                'task': task,
                'vendor': task.vendor,
                'recipient_name': recipient_name,
                'site_name': self.site_name,
                'days_until_due': task.days_until_due,
                'is_overdue': task.is_overdue,
                'dashboard_url': self._get_dashboard_url(),
                'task_url': self._get_task_url(task),
            }
            
            # Generate email content
            subject = self._generate_reminder_subject(task)
            text_content = self._render_reminder_text(context)
            html_content = self._render_reminder_html(context)
            
            # Send email
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=self.from_email,
                to=[recipient]
            )
            if html_content:
                msg.attach_alternative(html_content, "text/html")
            
            msg.send()
            
            # Update task reminder timestamp
            task.last_reminder_sent = timezone.now()
            task.save(update_fields=['last_reminder_sent'])
            
            logger.info(f"Task reminder sent for {task.task_id} to {recipient}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send task reminder for {task.task_id}: {str(e)}")
            return False
    
    def send_batch_reminders(self, tasks: List) -> Dict[str, int]:
        """
        Send reminder emails for multiple tasks.
        
        Args:
            tasks: List of VendorTask instances
            
        Returns:
            dict: Summary of sent/failed emails
        """
        results = {'sent': 0, 'failed': 0, 'skipped': 0}
        
        for task in tasks:
            if not task.should_send_reminder:
                results['skipped'] += 1
                continue
            
            # Send to assigned user
            success = False
            if task.assigned_to and task.assigned_to.email:
                success = self.send_task_reminder(task)
                if success:
                    results['sent'] += 1
                else:
                    results['failed'] += 1
            
            # Send to additional recipients
            for email in task.reminder_recipients:
                if email and self.send_task_reminder(task, email):
                    results['sent'] += 1
                else:
                    results['failed'] += 1
        
        logger.info(f"Batch reminders completed: {results}")
        return results
    
    def send_task_completion_notification(self, task) -> bool:
        """
        Send notification when a task is completed.
        
        Args:
            task: VendorTask instance that was completed
            
        Returns:
            bool: True if notification was sent successfully
        """
        try:
            # Notify task creator and stakeholders
            recipients = []
            
            if task.created_by and task.created_by.email:
                recipients.append((task.created_by.email, task.created_by.get_full_name()))
            
            if task.vendor.assigned_to and task.vendor.assigned_to.email:
                recipients.append((task.vendor.assigned_to.email, task.vendor.assigned_to.get_full_name()))
            
            # Remove duplicates
            recipients = list(set(recipients))
            
            if not recipients:
                return True  # No one to notify
            
            context = {
                'task': task,
                'vendor': task.vendor,
                'completed_by': task.assigned_to,
                'site_name': self.site_name,
                'task_url': self._get_task_url(task),
            }
            
            subject = f"Task Completed: {task.title} - {task.vendor.name}"
            text_content = self._render_completion_text(context)
            html_content = self._render_completion_html(context)
            
            for email, name in recipients:
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=self.from_email,
                    to=[email]
                )
                if html_content:
                    msg.attach_alternative(html_content, "text/html")
                msg.send()
            
            logger.info(f"Task completion notification sent for {task.task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send completion notification for {task.task_id}: {str(e)}")
            return False
    
    def send_overdue_escalation(self, tasks: List) -> bool:
        """
        Send escalation email for overdue tasks to management.
        
        Args:
            tasks: List of overdue VendorTask instances
            
        Returns:
            bool: True if escalation was sent successfully
        """
        if not tasks:
            return True
        
        try:
            # Get management email addresses (could be from settings or admin users)
            management_emails = self._get_management_emails()
            
            if not management_emails:
                logger.warning("No management emails configured for overdue escalation")
                return False
            
            context = {
                'overdue_tasks': tasks,
                'site_name': self.site_name,
                'dashboard_url': self._get_dashboard_url(),
                'total_overdue': len(tasks),
            }
            
            subject = f"Overdue Vendor Tasks Alert - {len(tasks)} Tasks Require Attention"
            text_content = self._render_escalation_text(context)
            html_content = self._render_escalation_html(context)
            
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=self.from_email,
                to=management_emails
            )
            if html_content:
                msg.attach_alternative(html_content, "text/html")
            
            msg.send()
            
            logger.info(f"Overdue escalation sent for {len(tasks)} tasks")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send overdue escalation: {str(e)}")
            return False
    
    def _generate_reminder_subject(self, task) -> str:
        """Generate email subject for task reminder."""
        days_until = task.days_until_due
        
        if task.is_overdue:
            return f"OVERDUE: {task.title} - {task.vendor.name}"
        elif days_until == 0:
            return f"DUE TODAY: {task.title} - {task.vendor.name}"
        elif days_until == 1:
            return f"DUE TOMORROW: {task.title} - {task.vendor.name}"
        else:
            return f"REMINDER: {task.title} - {task.vendor.name} (Due in {days_until} days)"
    
    def _render_reminder_text(self, context) -> str:
        """Render plain text reminder email."""
        return f"""
{context['recipient_name']},

This is a reminder about an upcoming vendor task:

Vendor: {context['vendor'].name}
Task: {context['task'].title}
Type: {context['task'].get_task_type_display()}
Due Date: {context['task'].due_date.strftime('%B %d, %Y')}
Priority: {context['task'].get_priority_display()}

{'This task is OVERDUE!' if context['is_overdue'] else f"Due in {context['days_until_due']} days."}

Description:
{context['task'].description or 'No description provided.'}

Please log into the {context['site_name']} to complete this task:
{context['dashboard_url']}

Best regards,
{context['site_name']} Team
"""
    
    def _render_reminder_html(self, context) -> str:
        """Render HTML reminder email."""
        # For now, return None to use text-only emails
        # In the future, this could render from an HTML template
        return None
    
    def _render_completion_text(self, context) -> str:
        """Render plain text completion notification."""
        return f"""
The following vendor task has been completed:

Vendor: {context['vendor'].name}
Task: {context['task'].title}
Completed By: {context['completed_by'].get_full_name() if context['completed_by'] else 'Unknown'}
Completed On: {context['task'].completed_date.strftime('%B %d, %Y at %I:%M %p')}

Completion Notes:
{context['task'].completion_notes or 'No completion notes provided.'}

View task details:
{context['task_url']}

Best regards,
{context['site_name']} Team
"""
    
    def _render_completion_html(self, context) -> str:
        """Render HTML completion notification."""
        return None
    
    def _render_escalation_text(self, context) -> str:
        """Render plain text escalation email."""
        task_list = "\n".join([
            f"- {task.title} ({task.vendor.name}) - {task.days_until_due * -1} days overdue"
            for task in context['overdue_tasks']
        ])
        
        return f"""
ATTENTION: Multiple vendor tasks are overdue and require immediate attention.

Total Overdue Tasks: {context['total_overdue']}

Overdue Tasks:
{task_list}

These tasks may impact vendor relationships, compliance requirements, or contract renewals.
Please review and assign resources to complete these tasks promptly.

Access the management dashboard:
{context['dashboard_url']}

Best regards,
{context['site_name']} Automated Monitoring
"""
    
    def _render_escalation_html(self, context) -> str:
        """Render HTML escalation email."""
        return None
    
    def _get_dashboard_url(self) -> str:
        """Get URL to the vendor task dashboard."""
        base_url = getattr(settings, 'SITE_URL', 'https://app.aximcyber.com')
        return f"{base_url}/admin/vendors/vendortask/"
    
    def _get_task_url(self, task) -> str:
        """Get URL to a specific task."""
        base_url = getattr(settings, 'SITE_URL', 'https://app.aximcyber.com')
        return f"{base_url}/admin/vendors/vendortask/{task.id}/"
    
    def _get_management_emails(self) -> List[str]:
        """Get list of management email addresses for escalations."""
        # Get from settings or admin users
        management_emails = getattr(settings, 'VENDOR_MANAGEMENT_EMAILS', [])
        
        if not management_emails:
            # Fallback to superuser emails
            admin_emails = User.objects.filter(
                is_superuser=True, 
                is_active=True,
                email__isnull=False
            ).exclude(email='').values_list('email', flat=True)
            management_emails = list(admin_emails)
        
        return management_emails


def get_notification_service() -> VendorTaskNotificationService:
    """Factory function to get notification service instance."""
    return VendorTaskNotificationService()


def send_daily_task_reminders() -> Dict[str, Any]:
    """
    Daily task to send all pending task reminders.
    This function is designed to be called by a scheduled task/cron job.
    
    Returns:
        dict: Summary of reminder sending results
    """
    from .models import VendorTask
    
    # Get tasks that need reminders today
    tasks_needing_reminders = VendorTask.objects.filter(
        status__in=['pending', 'in_progress', 'overdue'],
    ).select_related('vendor', 'assigned_to', 'created_by')
    
    # Filter to tasks that should send reminders today
    reminder_tasks = [task for task in tasks_needing_reminders if task.should_send_reminder]
    
    if not reminder_tasks:
        return {'status': 'success', 'message': 'No reminders needed today', 'sent': 0}
    
    # Send batch reminders
    notification_service = get_notification_service()
    results = notification_service.send_batch_reminders(reminder_tasks)
    
    # Check for overdue tasks that need escalation
    overdue_tasks = [task for task in tasks_needing_reminders if task.is_overdue]
    if overdue_tasks:
        notification_service.send_overdue_escalation(overdue_tasks)
        results['escalations_sent'] = 1
    
    return {
        'status': 'success',
        'message': f"Daily reminders completed",
        **results
    }