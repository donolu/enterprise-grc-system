from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core import mail
from unittest.mock import patch, MagicMock
from datetime import date, timedelta

from .models import (
    Framework, Clause, Control, ControlAssessment,
    AssessmentReminderConfiguration, AssessmentReminderLog
)
from .notifications import AssessmentReminderService, AssessmentNotificationService
from .tasks import send_due_reminders, send_immediate_reminder, test_reminder_configuration

User = get_user_model()


class AssessmentReminderConfigurationTest(TestCase):
    """Test AssessmentReminderConfiguration model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_get_or_create_for_user(self):
        """Test creating default configuration for user."""
        config = AssessmentReminderConfiguration.get_or_create_for_user(self.user)
        
        self.assertEqual(config.user, self.user)
        self.assertTrue(config.enable_reminders)
        self.assertEqual(config.advance_warning_days, 7)
        self.assertTrue(config.email_notifications)
        self.assertTrue(config.weekly_digest_enabled)
    
    def test_get_reminder_days_daily(self):
        """Test getting reminder days for daily frequency."""
        config = AssessmentReminderConfiguration.objects.create(
            user=self.user,
            reminder_frequency='daily',
            advance_warning_days=5
        )
        
        expected_days = [1, 2, 3, 4, 5]
        self.assertEqual(config.get_reminder_days(), expected_days)
    
    def test_get_reminder_days_weekly(self):
        """Test getting reminder days for weekly frequency."""
        config = AssessmentReminderConfiguration.objects.create(
            user=self.user,
            reminder_frequency='weekly'
        )
        
        expected_days = [7, 14, 21]
        self.assertEqual(config.get_reminder_days(), expected_days)
    
    def test_get_reminder_days_custom(self):
        """Test getting reminder days for custom frequency."""
        config = AssessmentReminderConfiguration.objects.create(
            user=self.user,
            reminder_frequency='custom',
            custom_reminder_days=[1, 3, 7, 14]
        )
        
        expected_days = [14, 7, 3, 1]  # Sorted in reverse
        self.assertEqual(config.get_reminder_days(), expected_days)


class AssessmentReminderLogTest(TestCase):
    """Test AssessmentReminderLog model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test framework and assessment
        self.framework = Framework.objects.create(
            name='Test Framework',
            short_name='TEST',
            version='1.0'
        )
        
        self.clause = Clause.objects.create(
            framework=self.framework,
            clause_id='T.1',
            title='Test Clause'
        )
        
        self.control = Control.objects.create(
            clause=self.clause,
            control_id='T.1.1',
            title='Test Control'
        )
        
        self.assessment = ControlAssessment.objects.create(
            control=self.control,
            assigned_to=self.user,
            due_date=timezone.now().date() + timedelta(days=7)
        )
    
    def test_reminder_log_creation(self):
        """Test creating a reminder log."""
        log = AssessmentReminderLog.objects.create(
            assessment=self.assessment,
            user=self.user,
            reminder_type='advance_warning',
            days_before_due=7,
            email_sent=True
        )
        
        self.assertEqual(log.assessment, self.assessment)
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.reminder_type, 'advance_warning')
        self.assertEqual(log.days_before_due, 7)
        self.assertTrue(log.email_sent)
    
    def test_unique_constraint(self):
        """Test that duplicate reminder logs cannot be created."""
        # Create first log
        AssessmentReminderLog.objects.create(
            assessment=self.assessment,
            user=self.user,
            reminder_type='advance_warning',
            days_before_due=7,
            email_sent=True
        )
        
        # Try to create duplicate - should fail
        with self.assertRaises(Exception):
            AssessmentReminderLog.objects.create(
                assessment=self.assessment,
                user=self.user,
                reminder_type='advance_warning',
                days_before_due=7,
                email_sent=False
            )


class AssessmentReminderServiceTest(TestCase):
    """Test AssessmentReminderService functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test assessment
        self.framework = Framework.objects.create(
            name='Test Framework',
            short_name='TEST',
            version='1.0'
        )
        
        self.clause = Clause.objects.create(
            framework=self.framework,
            clause_id='T.1',
            title='Test Clause'
        )
        
        self.control = Control.objects.create(
            clause=self.clause,
            control_id='T.1.1',
            title='Test Control',
            description='Test control description'
        )
        
        self.assessment = ControlAssessment.objects.create(
            control=self.control,
            assigned_to=self.user,
            due_date=timezone.now().date() + timedelta(days=7),
            status='in_progress'
        )
        
        # Clear any existing mail
        mail.outbox = []
    
    def test_send_individual_reminder_success(self):
        """Test sending individual reminder successfully."""
        # Create reminder configuration
        config = AssessmentReminderConfiguration.objects.create(
            user=self.user,
            enable_reminders=True,
            email_notifications=True
        )
        
        # Send reminder
        success = AssessmentReminderService.send_individual_reminder(
            self.assessment, self.user, 'advance_warning', 7
        )
        
        self.assertTrue(success)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.control.control_id, mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        
        # Check that log was created
        log = AssessmentReminderLog.objects.get(
            assessment=self.assessment,
            user=self.user,
            reminder_type='advance_warning'
        )
        self.assertTrue(log.email_sent)
    
    def test_send_individual_reminder_disabled(self):
        """Test that reminders are not sent when disabled."""
        # Create reminder configuration with reminders disabled
        config = AssessmentReminderConfiguration.objects.create(
            user=self.user,
            enable_reminders=False
        )
        
        # Send reminder
        success = AssessmentReminderService.send_individual_reminder(
            self.assessment, self.user, 'advance_warning', 7
        )
        
        self.assertFalse(success)
        self.assertEqual(len(mail.outbox), 0)
    
    def test_send_individual_reminder_duplicate_prevention(self):
        """Test that duplicate reminders are not sent."""
        # Create reminder configuration
        config = AssessmentReminderConfiguration.objects.create(
            user=self.user,
            enable_reminders=True,
            email_notifications=True
        )
        
        # Send first reminder
        success1 = AssessmentReminderService.send_individual_reminder(
            self.assessment, self.user, 'advance_warning', 7
        )
        
        # Try to send same reminder again
        success2 = AssessmentReminderService.send_individual_reminder(
            self.assessment, self.user, 'advance_warning', 7
        )
        
        self.assertTrue(success1)
        self.assertFalse(success2)  # Should be prevented
        self.assertEqual(len(mail.outbox), 1)  # Only one email sent
    
    def test_send_weekly_digest(self):
        """Test sending weekly digest."""
        # Create reminder configuration
        config = AssessmentReminderConfiguration.objects.create(
            user=self.user,
            weekly_digest_enabled=True,
            email_notifications=True
        )
        
        # Create overdue assessment
        overdue_assessment = ControlAssessment.objects.create(
            control=self.control,
            assigned_to=self.user,
            due_date=timezone.now().date() - timedelta(days=3),
            status='in_progress'
        )
        
        # Send digest
        success = AssessmentReminderService.send_weekly_digest(self.user)
        
        self.assertTrue(success)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Weekly Assessment Digest', mail.outbox[0].subject)
        self.assertIn('items require attention', mail.outbox[0].subject)
    
    def test_send_weekly_digest_no_assessments(self):
        """Test weekly digest when no assessments exist."""
        # Create reminder configuration
        config = AssessmentReminderConfiguration.objects.create(
            user=self.user,
            weekly_digest_enabled=True,
            email_notifications=True
        )
        
        # Delete the assessment
        self.assessment.delete()
        
        # Send digest
        success = AssessmentReminderService.send_weekly_digest(self.user)
        
        self.assertFalse(success)  # No digest sent when no assessments
        self.assertEqual(len(mail.outbox), 0)
    
    def test_get_urgency_info(self):
        """Test urgency classification logic."""
        # Test overdue
        urgency_class, message = AssessmentReminderService._get_urgency_info(
            self.assessment, 'overdue', -10
        )
        self.assertEqual(urgency_class, 'critical')
        self.assertIn('10 days overdue', message)
        
        # Test due today
        urgency_class, message = AssessmentReminderService._get_urgency_info(
            self.assessment, 'due_today', 0
        )
        self.assertEqual(urgency_class, 'high')
        self.assertEqual(message, 'DUE TODAY')
        
        # Test advance warning
        urgency_class, message = AssessmentReminderService._get_urgency_info(
            self.assessment, 'advance_warning', 2
        )
        self.assertEqual(urgency_class, 'medium')
        self.assertIn('Due in 2 days', message)
    
    def test_generate_subject_line(self):
        """Test email subject line generation."""
        # Test overdue subject
        subject = AssessmentReminderService._generate_subject_line(
            self.assessment, 'overdue', -5
        )
        self.assertIn('OVERDUE', subject)
        self.assertIn(self.control.control_id, subject)
        self.assertIn('5 days past due', subject)
        
        # Test due today subject
        subject = AssessmentReminderService._generate_subject_line(
            self.assessment, 'due_today', 0
        )
        self.assertIn('DUE TODAY', subject)
        self.assertIn(self.control.control_id, subject)
    
    @patch('catalogs.notifications.AssessmentReminderService.send_individual_reminder')
    @patch('catalogs.notifications.AssessmentReminderService.send_weekly_digest')
    def test_process_daily_reminders(self, mock_digest, mock_individual):
        """Test the main daily reminder processing."""
        # Set up mocks
        mock_individual.return_value = True
        mock_digest.return_value = True
        
        # Create reminder configuration
        config = AssessmentReminderConfiguration.objects.create(
            user=self.user,
            enable_reminders=True,
            email_notifications=True,
            advance_warning_days=7,
            weekly_digest_enabled=True,
            digest_day_of_week=timezone.now().weekday()  # Today
        )
        
        # Set assessment due in 7 days (should trigger advance warning)
        self.assessment.due_date = timezone.now().date() + timedelta(days=7)
        self.assessment.save()
        
        # Process reminders
        results = AssessmentReminderService.process_daily_reminders()
        
        # Verify results
        self.assertEqual(results['processed_users'], 1)
        self.assertTrue(mock_individual.called)
        self.assertTrue(mock_digest.called)


class AssessmentNotificationServiceTest(TestCase):
    """Test AssessmentNotificationService functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.framework = Framework.objects.create(
            name='Test Framework',
            short_name='TEST',
            version='1.0'
        )
        
        self.clause = Clause.objects.create(
            framework=self.framework,
            clause_id='T.1',
            title='Test Clause'
        )
        
        self.control = Control.objects.create(
            clause=self.clause,
            control_id='T.1.1',
            title='Test Control'
        )
        
        self.assessment = ControlAssessment.objects.create(
            control=self.control,
            assigned_to=self.user
        )
        
        # Clear mail
        mail.outbox = []
    
    def test_send_assignment_notification(self):
        """Test sending assignment notification."""
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com'
        )
        
        success = AssessmentNotificationService.send_assignment_notification(
            self.assessment, admin_user
        )
        
        self.assertTrue(success)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('New Assessment Assignment', mail.outbox[0].subject)
        self.assertIn(self.control.control_id, mail.outbox[0].subject)
    
    def test_send_status_change_notification(self):
        """Test sending status change notification."""
        success = AssessmentNotificationService.send_status_change_notification(
            self.assessment, 'not_started', 'in_progress'
        )
        
        self.assertTrue(success)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Assessment Status Updated', mail.outbox[0].subject)
        self.assertIn('In Progress', mail.outbox[0].subject)
    
    def test_send_status_change_notification_insignificant(self):
        """Test that insignificant status changes don't send notifications."""
        success = AssessmentNotificationService.send_status_change_notification(
            self.assessment, 'pending', 'not_started'
        )
        
        self.assertFalse(success)
        self.assertEqual(len(mail.outbox), 0)


class ReminderTasksTest(TestCase):
    """Test reminder Celery tasks."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        mail.outbox = []
    
    @patch('catalogs.notifications.AssessmentReminderService.process_daily_reminders')
    def test_send_due_reminders_task(self, mock_process):
        """Test the main send_due_reminders task."""
        # Mock the service response
        mock_process.return_value = {
            'advance_warnings_sent': 2,
            'due_today_sent': 1,
            'overdue_sent': 3,
            'weekly_digests_sent': 1,
            'errors': [],
            'processed_users': 5
        }
        
        # Call the task
        result = send_due_reminders()
        
        # Verify task response
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['total_emails_sent'], 7)
        self.assertEqual(result['users_processed'], 5)
        self.assertTrue(mock_process.called)
    
    @patch('catalogs.notifications.AssessmentReminderService.send_individual_reminder')
    def test_send_immediate_reminder_task(self, mock_send):
        """Test sending immediate reminder task."""
        # Create test assessment
        framework = Framework.objects.create(name='Test', short_name='TEST', version='1.0')
        clause = Clause.objects.create(framework=framework, clause_id='T.1', title='Test')
        control = Control.objects.create(clause=clause, control_id='T.1.1', title='Test')
        assessment = ControlAssessment.objects.create(control=control, assigned_to=self.user)
        
        # Mock service response
        mock_send.return_value = True
        
        # Call the task
        result = send_immediate_reminder(assessment.id, self.user.id, 'due_today')
        
        # Verify task response
        self.assertEqual(result['status'], 'success')
        self.assertTrue(result['email_sent'])
        self.assertTrue(mock_send.called)
    
    def test_test_reminder_configuration_task(self):
        """Test the reminder configuration test task."""
        # Call the task
        result = test_reminder_configuration(self.user.id)
        
        # Verify task response
        self.assertEqual(result['status'], 'success')
        self.assertTrue(result['email_sent'])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Test Reminder', mail.outbox[0].subject)


class ReminderIntegrationTest(TestCase):
    """Integration tests for the complete reminder system."""
    
    def setUp(self):
        # Create users
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        
        # Create framework structure
        self.framework = Framework.objects.create(
            name='ISO 27001',
            short_name='ISO27001',
            version='2022'
        )
        
        self.clause = Clause.objects.create(
            framework=self.framework,
            clause_id='A.5.1',
            title='Policies for information security'
        )
        
        self.control = Control.objects.create(
            clause=self.clause,
            control_id='A.5.1.1',
            title='Information security policies'
        )
        
        # Clear mail
        mail.outbox = []
    
    def test_end_to_end_reminder_workflow(self):
        """Test complete reminder workflow from configuration to delivery."""
        # Create reminder configurations
        config1 = AssessmentReminderConfiguration.objects.create(
            user=self.user1,
            enable_reminders=True,
            email_notifications=True,
            advance_warning_days=7,
            reminder_frequency='daily'
        )
        
        config2 = AssessmentReminderConfiguration.objects.create(
            user=self.user2,
            enable_reminders=False  # Disabled
        )
        
        # Create assessments
        assessment1 = ControlAssessment.objects.create(
            control=self.control,
            assigned_to=self.user1,
            due_date=timezone.now().date() + timedelta(days=7),  # 7 days away
            status='in_progress'
        )
        
        assessment2 = ControlAssessment.objects.create(
            control=self.control,
            assigned_to=self.user2,
            due_date=timezone.now().date() + timedelta(days=7),  # 7 days away
            status='in_progress'
        )
        
        # Process daily reminders
        results = AssessmentReminderService.process_daily_reminders()
        
        # Verify results
        self.assertEqual(results['processed_users'], 2)
        self.assertEqual(results['advance_warnings_sent'], 1)  # Only user1 should get reminder
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user1.email])
        
        # Verify reminder log was created for user1 only
        self.assertTrue(
            AssessmentReminderLog.objects.filter(
                assessment=assessment1,
                user=self.user1,
                reminder_type='advance_warning'
            ).exists()
        )
        
        self.assertFalse(
            AssessmentReminderLog.objects.filter(
                assessment=assessment2,
                user=self.user2
            ).exists()
        )
    
    def test_overdue_reminder_escalation(self):
        """Test overdue reminder behavior."""
        # Create configuration
        config = AssessmentReminderConfiguration.objects.create(
            user=self.user1,
            enable_reminders=True,
            email_notifications=True,
            overdue_reminders=True,
            reminder_frequency='daily'
        )
        
        # Create overdue assessment
        assessment = ControlAssessment.objects.create(
            control=self.control,
            assigned_to=self.user1,
            due_date=timezone.now().date() - timedelta(days=5),  # 5 days overdue
            status='in_progress'
        )
        
        # Process daily reminders
        results = AssessmentReminderService.process_daily_reminders()
        
        # Verify overdue reminder was sent
        self.assertEqual(results['overdue_sent'], 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('OVERDUE', mail.outbox[0].subject)
        self.assertIn('5 days past due', mail.outbox[0].subject)