import json
from datetime import date, timedelta
from unittest.mock import patch, MagicMock, call
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from django.template.loader import render_to_string

from ..models import (
    Risk, RiskCategory, RiskAction, RiskActionNote, 
    RiskActionEvidence, RiskActionReminderConfiguration, RiskActionReminderLog
)
from ..notifications import RiskActionReminderService, RiskActionNotificationService

User = get_user_model()


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    CELERY_TASK_ALWAYS_EAGER=True
)
class RiskActionReminderServiceTest(TestCase):
    """Test cases for RiskActionReminderService."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )
        self.category = RiskCategory.objects.create(
            name='Test Category',
            code='TEST'
        )
        self.risk = Risk.objects.create(
            title='Test Risk',
            description='Test risk for notifications',
            category=self.category,
            risk_owner=self.user,
            impact=4,
            likelihood=3,
            risk_level='high'
        )
        
        # Create reminder configuration for user
        self.config = RiskActionReminderConfiguration.objects.create(
            user=self.user,
            enabled=True,
            send_due_reminders=True,
            send_overdue_reminders=True,
            reminder_days_before=7
        )
    
    def test_send_individual_reminder_due_soon(self):
        """Test sending individual reminder for action due soon."""
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Test Action Due Soon',
            description='Action due in 3 days',
            action_type='mitigation',
            priority='high',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=3),
            status='in_progress'
        )
        
        # Clear any existing mail
        mail.outbox = []
        
        result = RiskActionReminderService.send_individual_reminder(
            action, self.user, 'due_soon', 3
        )
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.user.email])
        self.assertIn('Risk Action Reminder', email.subject)
        self.assertIn('due in 3 days', email.body)
        self.assertIn(action.title, email.body)
        self.assertIn(action.action_id, email.body)
        
        # Check that reminder log was created
        log_entry = RiskActionReminderLog.objects.filter(
            action=action,
            user=self.user,
            reminder_type='due_soon'
        ).first()
        self.assertIsNotNone(log_entry)
        self.assertTrue(log_entry.sent_successfully)
    
    def test_send_individual_reminder_due_today(self):
        """Test sending reminder for action due today."""
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Action Due Today',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today(),
            status='pending'
        )
        
        mail.outbox = []
        
        result = RiskActionReminderService.send_individual_reminder(
            action, self.user, 'due_today', 0
        )
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        
        email = mail.outbox[0]
        self.assertIn('due today', email.body)
        self.assertIn('URGENT', email.subject)
    
    def test_send_individual_reminder_overdue(self):
        """Test sending reminder for overdue action."""
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Overdue Action',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() - timedelta(days=2),
            status='in_progress'
        )
        
        mail.outbox = []
        
        result = RiskActionReminderService.send_individual_reminder(
            action, self.user, 'overdue', -2
        )
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        
        email = mail.outbox[0]
        self.assertIn('overdue by 2 days', email.body)
        self.assertIn('OVERDUE', email.subject)
    
    def test_send_reminder_disabled_user(self):
        """Test that reminders are not sent to users with disabled notifications."""
        self.config.enabled = False
        self.config.save()
        
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Test Action',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today(),
            status='pending'
        )
        
        mail.outbox = []
        
        result = RiskActionReminderService.send_individual_reminder(
            action, self.user, 'due_today', 0
        )
        
        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)
    
    def test_send_reminder_specific_type_disabled(self):
        """Test that specific reminder types can be disabled."""
        self.config.send_due_reminders = False
        self.config.save()
        
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Test Action',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today(),
            status='pending'
        )
        
        mail.outbox = []
        
        result = RiskActionReminderService.send_individual_reminder(
            action, self.user, 'due_today', 0
        )
        
        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)
    
    def test_process_due_reminders(self):
        """Test processing all due reminders."""
        # Create actions with different due dates
        action1 = RiskAction.objects.create(
            risk=self.risk,
            title='Due in 7 days',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=7),
            status='pending'
        )
        action2 = RiskAction.objects.create(
            risk=self.risk,
            title='Due today',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today(),
            status='in_progress'
        )
        action3 = RiskAction.objects.create(
            risk=self.risk,
            title='Overdue',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() - timedelta(days=1),
            status='pending'
        )
        
        mail.outbox = []
        
        with patch('risk.notifications.RiskActionReminderService.send_individual_reminder') as mock_send:
            mock_send.return_value = True
            
            result = RiskActionReminderService.process_due_reminders()
            
            self.assertIsNotNone(result)
            # Should be called for advance warning (7 days), due today, and overdue
            self.assertEqual(mock_send.call_count, 3)
    
    def test_get_user_actions_summary(self):
        """Test getting action summary for user."""
        # Create various actions for user
        RiskAction.objects.create(
            risk=self.risk,
            title='Pending Action',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=5),
            status='pending'
        )
        RiskAction.objects.create(
            risk=self.risk,
            title='In Progress Action',
            action_type='acceptance',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=10),
            status='in_progress',
            progress_percentage=50
        )
        RiskAction.objects.create(
            risk=self.risk,
            title='Completed Action',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() - timedelta(days=5),
            status='completed'
        )
        RiskAction.objects.create(
            risk=self.risk,
            title='Overdue Action',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() - timedelta(days=2),
            status='pending'
        )
        
        summary = RiskActionReminderService.get_user_actions_summary(self.user)
        
        self.assertEqual(summary['total_assigned'], 4)
        self.assertEqual(summary['pending'], 1)
        self.assertEqual(summary['in_progress'], 1)
        self.assertEqual(summary['completed'], 1)
        self.assertEqual(summary['overdue'], 1)
        self.assertEqual(summary['due_this_week'], 1)  # The one due in 5 days
        self.assertIn('due_soon_actions', summary)
        self.assertIn('overdue_actions', summary)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
)
class RiskActionNotificationServiceTest(TestCase):
    """Test cases for RiskActionNotificationService."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )
        self.category = RiskCategory.objects.create(
            name='Test Category',
            code='TEST'
        )
        self.risk = Risk.objects.create(
            title='Test Risk',
            category=self.category,
            risk_owner=self.user,
            impact=3,
            likelihood=3
        )
        
        # Create notification configuration
        self.config = RiskActionReminderConfiguration.objects.create(
            user=self.user,
            enabled=True,
            send_assignment_notifications=True,
            send_status_change_notifications=True,
            send_evidence_notifications=True
        )
    
    def test_notify_assignment(self):
        """Test assignment notification."""
        action = RiskAction.objects.create(
            risk=self.risk,
            title='New Assignment',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=14),
            status='pending'
        )
        
        mail.outbox = []
        
        result = RiskActionNotificationService.notify_assignment(action, self.user)
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.user.email])
        self.assertIn('Risk Action Assignment', email.subject)
        self.assertIn(action.title, email.body)
        self.assertIn(action.action_id, email.body)
        self.assertIn('assigned to you', email.body)
    
    def test_notify_status_change(self):
        """Test status change notification."""
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Status Change Action',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=14),
            status='pending'
        )
        
        mail.outbox = []
        
        result = RiskActionNotificationService.notify_status_change(
            action, 'pending', 'in_progress', self.user
        )
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        
        email = mail.outbox[0]
        self.assertIn('Risk Action Status Update', email.subject)
        self.assertIn('pending', email.body)
        self.assertIn('in_progress', email.body)
        self.assertIn(action.title, email.body)
    
    def test_notify_evidence_uploaded(self):
        """Test evidence upload notification."""
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Evidence Action',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=14),
            status='in_progress'
        )
        
        evidence = RiskActionEvidence.objects.create(
            action=action,
            title='Test Evidence',
            evidence_type='document',
            description='Test evidence upload',
            uploaded_by=self.user
        )
        
        mail.outbox = []
        
        result = RiskActionNotificationService.notify_evidence_uploaded(evidence, self.user)
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        
        email = mail.outbox[0]
        self.assertIn('Risk Action Evidence Uploaded', email.subject)
        self.assertIn(evidence.title, email.body)
        self.assertIn(action.title, email.body)
    
    def test_send_weekly_digest(self):
        """Test sending weekly digest."""
        # Create some actions for the user
        RiskAction.objects.create(
            risk=self.risk,
            title='Weekly Action 1',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=5),
            status='pending'
        )
        RiskAction.objects.create(
            risk=self.risk,
            title='Weekly Action 2',
            action_type='acceptance',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=12),
            status='in_progress'
        )
        
        mail.outbox = []
        
        result = RiskActionNotificationService.send_weekly_digest(self.user)
        
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.user.email])
        self.assertIn('Weekly Risk Action Digest', email.subject)
        self.assertIn('Weekly Action 1', email.body)
        self.assertIn('Weekly Action 2', email.body)
    
    def test_notification_disabled_user(self):
        """Test that notifications are not sent to users with disabled settings."""
        self.config.send_assignment_notifications = False
        self.config.save()
        
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Disabled Notification',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=14),
            status='pending'
        )
        
        mail.outbox = []
        
        result = RiskActionNotificationService.notify_assignment(action, self.user)
        
        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)
    
    def test_get_notification_recipients(self):
        """Test getting notification recipients for an action."""
        # Create additional users
        user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Multi-recipient Action',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=14),
            status='pending'
        )
        
        recipients = RiskActionNotificationService.get_notification_recipients(action, 'assignment')
        
        # Should include assigned user and risk owner
        expected_emails = {self.user.email}
        actual_emails = {recipient.email for recipient in recipients}
        
        self.assertEqual(actual_emails, expected_emails)
    
    @patch('risk.notifications.logger')
    def test_email_send_failure_logging(self, mock_logger):
        """Test that email send failures are properly logged."""
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Failed Email Action',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=14),
            status='pending'
        )
        
        with patch('risk.notifications.send_mail', side_effect=Exception('SMTP Error')):
            result = RiskActionNotificationService.notify_assignment(action, self.user)
            
            self.assertFalse(result)
            mock_logger.error.assert_called()
    
    def test_template_rendering(self):
        """Test that email templates render correctly."""
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Template Test Action',
            description='Action for testing template rendering',
            action_type='mitigation',
            priority='high',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=7),
            status='pending'
        )
        
        # Test HTML template rendering
        html_content = render_to_string('emails/risk_action_assignment.html', {
            'user': self.user,
            'action': action,
            'action_url': f'http://example.com/actions/{action.id}',
            'site_domain': 'example.com'
        })
        
        self.assertIn(action.title, html_content)
        self.assertIn(action.action_id, html_content)
        self.assertIn(action.get_priority_display(), html_content)
        self.assertIn('high priority', html_content.lower())
        
        # Test text template rendering
        text_content = render_to_string('emails/risk_action_assignment.txt', {
            'user': self.user,
            'action': action,
            'action_url': f'http://example.com/actions/{action.id}',
            'site_domain': 'example.com'
        })
        
        self.assertIn(action.title, text_content)
        self.assertIn(action.action_id, text_content)
        self.assertIn('Template Test Action', text_content)


class RiskActionReminderLogTest(TestCase):
    """Test cases for RiskActionReminderLog model and functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = RiskCategory.objects.create(
            name='Test Category',
            code='TEST'
        )
        self.risk = Risk.objects.create(
            title='Test Risk',
            category=self.category,
            risk_owner=self.user,
            impact=3,
            likelihood=3
        )
        self.action = RiskAction.objects.create(
            risk=self.risk,
            title='Test Action',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=7)
        )
    
    def test_reminder_log_creation(self):
        """Test creating reminder log entries."""
        log_entry = RiskActionReminderLog.objects.create(
            action=self.action,
            user=self.user,
            reminder_type='due_soon',
            sent_successfully=True
        )
        
        self.assertEqual(log_entry.action, self.action)
        self.assertEqual(log_entry.user, self.user)
        self.assertEqual(log_entry.reminder_type, 'due_soon')
        self.assertTrue(log_entry.sent_successfully)
        self.assertIsNotNone(log_entry.sent_at)
    
    def test_prevent_duplicate_reminders(self):
        """Test prevention of duplicate reminders within same day."""
        # Create initial log entry
        RiskActionReminderLog.objects.create(
            action=self.action,
            user=self.user,
            reminder_type='due_soon',
            sent_successfully=True
        )
        
        # Check if reminder was already sent today
        today = timezone.now().date()
        existing_log = RiskActionReminderLog.objects.filter(
            action=self.action,
            user=self.user,
            reminder_type='due_soon',
            sent_at__date=today
        ).exists()
        
        self.assertTrue(existing_log)
    
    def test_failed_reminder_log(self):
        """Test logging failed reminder attempts."""
        log_entry = RiskActionReminderLog.objects.create(
            action=self.action,
            user=self.user,
            reminder_type='overdue',
            sent_successfully=False,
            error_message='SMTP connection failed'
        )
        
        self.assertFalse(log_entry.sent_successfully)
        self.assertEqual(log_entry.error_message, 'SMTP connection failed')
    
    def test_reminder_statistics(self):
        """Test getting reminder statistics."""
        # Create various log entries
        RiskActionReminderLog.objects.create(
            action=self.action,
            user=self.user,
            reminder_type='due_soon',
            sent_successfully=True
        )
        RiskActionReminderLog.objects.create(
            action=self.action,
            user=self.user,
            reminder_type='overdue',
            sent_successfully=True
        )
        RiskActionReminderLog.objects.create(
            action=self.action,
            user=self.user,
            reminder_type='due_today',
            sent_successfully=False,
            error_message='Email validation failed'
        )
        
        total_logs = RiskActionReminderLog.objects.filter(action=self.action).count()
        successful_logs = RiskActionReminderLog.objects.filter(
            action=self.action,
            sent_successfully=True
        ).count()
        failed_logs = RiskActionReminderLog.objects.filter(
            action=self.action,
            sent_successfully=False
        ).count()
        
        self.assertEqual(total_logs, 3)
        self.assertEqual(successful_logs, 2)
        self.assertEqual(failed_logs, 1)