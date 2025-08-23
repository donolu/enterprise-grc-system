from datetime import date, timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from celery.exceptions import Retry

from ..models import (
    Risk, RiskCategory, RiskAction, RiskActionReminderConfiguration, RiskActionReminderLog
)
from ..tasks import (
    send_risk_action_due_reminders, send_risk_action_weekly_digests,
    send_immediate_risk_action_reminder, cleanup_old_risk_action_reminder_logs
)

User = get_user_model()


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True
)
class RiskActionTaskTest(TestCase):
    """Test cases for risk action Celery tasks."""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            first_name='User',
            last_name='One',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            first_name='User',
            last_name='Two',
            password='testpass123'
        )
        
        self.category = RiskCategory.objects.create(
            name='Test Category',
            code='TEST'
        )
        self.risk = Risk.objects.create(
            title='Test Risk',
            category=self.category,
            risk_owner=self.user1,
            impact=4,
            likelihood=3,
            risk_level='high'
        )
        
        # Create reminder configurations
        RiskActionReminderConfiguration.objects.create(
            user=self.user1,
            enabled=True,
            send_due_reminders=True,
            send_overdue_reminders=True,
            reminder_days_before=7
        )
        RiskActionReminderConfiguration.objects.create(
            user=self.user2,
            enabled=True,
            send_due_reminders=True,
            send_overdue_reminders=True,
            reminder_days_before=3
        )
    
    @patch('risk.notifications.RiskActionReminderService.send_individual_reminder')
    def test_send_due_reminders_task_success(self, mock_send_reminder):
        """Test successful execution of due reminders task."""
        mock_send_reminder.return_value = True
        
        # Create actions with different due dates
        RiskAction.objects.create(
            risk=self.risk,
            title='Due in 7 days',
            action_type='mitigation',
            assigned_to=self.user1,
            due_date=date.today() + timedelta(days=7),
            status='pending'
        )
        RiskAction.objects.create(
            risk=self.risk,
            title='Due in 3 days',
            action_type='mitigation',
            assigned_to=self.user2,
            due_date=date.today() + timedelta(days=3),
            status='in_progress'
        )
        RiskAction.objects.create(
            risk=self.risk,
            title='Due today',
            action_type='acceptance',
            assigned_to=self.user1,
            due_date=date.today(),
            status='pending'
        )
        RiskAction.objects.create(
            risk=self.risk,
            title='Overdue by 1 day',
            action_type='mitigation',
            assigned_to=self.user2,
            due_date=date.today() - timedelta(days=1),
            status='in_progress'
        )
        
        # Run the task
        result = send_risk_action_due_reminders.apply()
        
        self.assertTrue(result.successful())
        self.assertIsInstance(result.result, dict)
        
        # Should send reminders for actions matching user preferences
        # user1: 7 days advance + due today + (no overdue since different user)
        # user2: 3 days advance + overdue
        expected_calls = 4  # All actions should get reminders
        self.assertEqual(mock_send_reminder.call_count, expected_calls)
    
    @patch('risk.notifications.RiskActionReminderService.send_individual_reminder')
    def test_send_due_reminders_excludes_completed_actions(self, mock_send_reminder):
        """Test that completed actions are excluded from reminders."""
        mock_send_reminder.return_value = True
        
        # Create completed action that would normally trigger reminder
        RiskAction.objects.create(
            risk=self.risk,
            title='Completed action',
            action_type='mitigation',
            assigned_to=self.user1,
            due_date=date.today(),
            status='completed'
        )
        
        # Create active action for comparison
        RiskAction.objects.create(
            risk=self.risk,
            title='Active action',
            action_type='mitigation',
            assigned_to=self.user1,
            due_date=date.today(),
            status='pending'
        )
        
        result = send_risk_action_due_reminders.apply()
        
        self.assertTrue(result.successful())
        # Should only send reminder for active action
        self.assertEqual(mock_send_reminder.call_count, 1)
    
    @patch('risk.notifications.RiskActionReminderService.send_individual_reminder')
    def test_send_due_reminders_respects_user_preferences(self, mock_send_reminder):
        """Test that reminders respect user notification preferences."""
        mock_send_reminder.return_value = True
        
        # Disable reminders for user2
        config = RiskActionReminderConfiguration.objects.get(user=self.user2)
        config.enabled = False
        config.save()
        
        # Create actions for both users
        RiskAction.objects.create(
            risk=self.risk,
            title='Action for user1',
            action_type='mitigation',
            assigned_to=self.user1,
            due_date=date.today(),
            status='pending'
        )
        RiskAction.objects.create(
            risk=self.risk,
            title='Action for user2',
            action_type='mitigation',
            assigned_to=self.user2,
            due_date=date.today(),
            status='pending'
        )
        
        result = send_risk_action_due_reminders.apply()
        
        self.assertTrue(result.successful())
        # Should only send reminder for user1
        self.assertEqual(mock_send_reminder.call_count, 1)
    
    @patch('risk.notifications.RiskActionReminderService.send_individual_reminder')
    def test_send_due_reminders_handles_exceptions(self, mock_send_reminder):
        """Test that task handles exceptions gracefully."""
        # First call succeeds, second fails
        mock_send_reminder.side_effect = [True, Exception('SMTP Error'), True]
        
        # Create actions
        for i in range(3):
            RiskAction.objects.create(
                risk=self.risk,
                title=f'Action {i}',
                action_type='mitigation',
                assigned_to=self.user1,
                due_date=date.today(),
                status='pending'
            )
        
        result = send_risk_action_due_reminders.apply()
        
        self.assertTrue(result.successful())
        # Should attempt all reminders despite one failing
        self.assertEqual(mock_send_reminder.call_count, 3)
    
    @patch('risk.notifications.RiskActionReminderService.send_individual_reminder')
    def test_send_due_reminders_prevents_duplicate_daily_reminders(self, mock_send_reminder):
        """Test that duplicate reminders are not sent on same day."""
        mock_send_reminder.return_value = True
        
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Test Action',
            action_type='mitigation',
            assigned_to=self.user1,
            due_date=date.today(),
            status='pending'
        )
        
        # Create existing log entry for today
        RiskActionReminderLog.objects.create(
            action=action,
            user=self.user1,
            reminder_type='due_today',
            sent_successfully=True
        )
        
        result = send_risk_action_due_reminders.apply()
        
        self.assertTrue(result.successful())
        # Should not send duplicate reminder
        mock_send_reminder.assert_not_called()
    
    @patch('risk.notifications.RiskActionNotificationService.send_weekly_digest')
    def test_weekly_digest_task_success(self, mock_send_digest):
        """Test successful execution of weekly digest task."""
        mock_send_digest.return_value = True
        
        # Create some actions for users
        RiskAction.objects.create(
            risk=self.risk,
            title='User1 Action',
            action_type='mitigation',
            assigned_to=self.user1,
            due_date=date.today() + timedelta(days=5),
            status='in_progress'
        )
        RiskAction.objects.create(
            risk=self.risk,
            title='User2 Action',
            action_type='acceptance',
            assigned_to=self.user2,
            due_date=date.today() + timedelta(days=10),
            status='pending'
        )
        
        result = send_risk_action_weekly_digests.apply()
        
        self.assertTrue(result.successful())
        self.assertIsInstance(result.result, dict)
        
        # Should send digest to both users
        self.assertEqual(mock_send_digest.call_count, 2)
        
        # Verify users were called
        called_users = [call[0][0] for call in mock_send_digest.call_args_list]
        self.assertIn(self.user1, called_users)
        self.assertIn(self.user2, called_users)
    
    @patch('risk.notifications.RiskActionNotificationService.send_weekly_digest')
    def test_weekly_digest_respects_user_preferences(self, mock_send_digest):
        """Test that weekly digest respects user preferences."""
        mock_send_digest.return_value = True
        
        # Disable weekly digest for user2
        config = RiskActionReminderConfiguration.objects.get(user=self.user2)
        config.send_weekly_digest = False
        config.save()
        
        # Create actions for both users
        RiskAction.objects.create(
            risk=self.risk,
            title='User1 Action',
            action_type='mitigation',
            assigned_to=self.user1,
            due_date=date.today() + timedelta(days=5)
        )
        RiskAction.objects.create(
            risk=self.risk,
            title='User2 Action',
            action_type='mitigation',
            assigned_to=self.user2,
            due_date=date.today() + timedelta(days=5)
        )
        
        result = send_risk_action_weekly_digests.apply()
        
        self.assertTrue(result.successful())
        # Should only send digest to user1
        self.assertEqual(mock_send_digest.call_count, 1)
        self.assertEqual(mock_send_digest.call_args[0][0], self.user1)
    
    @patch('risk.notifications.RiskActionNotificationService.send_weekly_digest')
    def test_weekly_digest_handles_exceptions(self, mock_send_digest):
        """Test that weekly digest task handles exceptions gracefully."""
        # First call succeeds, second fails
        mock_send_digest.side_effect = [True, Exception('Email service unavailable')]
        
        # Create actions for both users
        RiskAction.objects.create(
            risk=self.risk,
            title='User1 Action',
            action_type='mitigation',
            assigned_to=self.user1,
            due_date=date.today() + timedelta(days=5)
        )
        RiskAction.objects.create(
            risk=self.risk,
            title='User2 Action',
            action_type='mitigation',
            assigned_to=self.user2,
            due_date=date.today() + timedelta(days=5)
        )
        
        result = send_risk_action_weekly_digests.apply()
        
        self.assertTrue(result.successful())
        # Should attempt digest for both users despite one failing
        self.assertEqual(mock_send_digest.call_count, 2)
    
    @patch('risk.notifications.RiskActionReminderService.send_individual_reminder')
    def test_process_individual_reminder_task(self, mock_send_reminder):
        """Test individual reminder processing task."""
        mock_send_reminder.return_value = True
        
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Individual Reminder Action',
            action_type='mitigation',
            assigned_to=self.user1,
            due_date=date.today() + timedelta(days=3),
            status='pending'
        )
        
        result = send_immediate_risk_action_reminder.apply(args=[
            action.id, self.user1.id, 'due_soon', 3
        ])
        
        self.assertTrue(result.successful())
        mock_send_reminder.assert_called_once_with(action, self.user1, 'due_soon', 3)
    
    @patch('risk.notifications.RiskActionReminderService.send_individual_reminder')
    def test_process_individual_reminder_task_retry(self, mock_send_reminder):
        """Test that individual reminder task retries on failure."""
        mock_send_reminder.side_effect = Exception('Temporary failure')
        
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Retry Action',
            action_type='mitigation',
            assigned_to=self.user1,
            due_date=date.today() + timedelta(days=3),
            status='pending'
        )
        
        with self.assertRaises(Exception):
            # Task should raise exception after max retries
            send_immediate_risk_action_reminder.apply(args=[
                action.id, self.user1.id, 'due_soon', 3
            ])
    
    def test_cleanup_old_reminder_logs_task(self):
        """Test cleanup of old reminder logs."""
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Cleanup Test Action',
            action_type='mitigation',
            assigned_to=self.user1,
            due_date=date.today() + timedelta(days=30),
            status='pending'
        )
        
        # Create old log entries (older than 90 days)
        old_date = timezone.now() - timedelta(days=100)
        RiskActionReminderLog.objects.create(
            action=action,
            user=self.user1,
            reminder_type='due_soon',
            sent_successfully=True,
            sent_at=old_date
        )
        RiskActionReminderLog.objects.create(
            action=action,
            user=self.user1,
            reminder_type='overdue',
            sent_successfully=True,
            sent_at=old_date
        )
        
        # Create recent log entry (should not be deleted)
        recent_date = timezone.now() - timedelta(days=30)
        RiskActionReminderLog.objects.create(
            action=action,
            user=self.user1,
            reminder_type='due_today',
            sent_successfully=True,
            sent_at=recent_date
        )
        
        self.assertEqual(RiskActionReminderLog.objects.count(), 3)
        
        result = cleanup_old_risk_action_reminder_logs.apply()
        
        self.assertTrue(result.successful())
        self.assertEqual(RiskActionReminderLog.objects.count(), 1)
        
        # Verify that only recent log remains
        remaining_log = RiskActionReminderLog.objects.first()
        self.assertEqual(remaining_log.reminder_type, 'due_today')
    
    @patch('risk.tasks.logger')
    def test_task_error_logging(self, mock_logger):
        """Test that task errors are properly logged."""
        with patch('risk.models.User.objects.filter') as mock_filter:
            # Simulate database error
            mock_filter.side_effect = Exception('Database connection failed')
            
            result = send_risk_action_due_reminders.apply()
            
            # Task should handle error gracefully
            self.assertTrue(result.successful())
            # Error should be logged
            mock_logger.error.assert_called()
    
    def test_task_result_statistics(self):
        """Test that tasks return proper statistics."""
        # Create test actions
        for i in range(3):
            RiskAction.objects.create(
                risk=self.risk,
                title=f'Stats Action {i}',
                action_type='mitigation',
                assigned_to=self.user1,
                due_date=date.today() + timedelta(days=i),
                status='pending'
            )
        
        with patch('risk.notifications.RiskActionReminderService.send_individual_reminder') as mock_send:
            mock_send.return_value = True
            
            result = send_risk_action_due_reminders.apply()
            
            self.assertTrue(result.successful())
            stats = result.result
            
            self.assertIn('total_users_processed', stats)
            self.assertIn('total_reminders_sent', stats)
            self.assertIn('total_errors', stats)
            self.assertIn('processing_time', stats)
            
            self.assertGreaterEqual(stats['total_users_processed'], 1)
            self.assertGreaterEqual(stats['total_reminders_sent'], 0)
            self.assertEqual(stats['total_errors'], 0)
    
    @patch('risk.notifications.RiskActionReminderService.send_individual_reminder')
    def test_reminder_frequency_control(self, mock_send_reminder):
        """Test that reminder frequency is controlled properly."""
        mock_send_reminder.return_value = True
        
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Frequency Test Action',
            action_type='mitigation',
            assigned_to=self.user1,
            due_date=date.today() + timedelta(days=2),
            status='pending'
        )
        
        # First reminder should be sent
        result = send_risk_action_due_reminders.apply()
        self.assertTrue(result.successful())
        
        # Reset mock
        mock_send_reminder.reset_mock()
        
        # Immediate second run should not send duplicate reminders
        result = send_risk_action_due_reminders.apply()
        self.assertTrue(result.successful())
        
        # Should not send reminder again for same day
        mock_send_reminder.assert_not_called()
    
    def test_task_performance_with_large_dataset(self):
        """Test task performance with larger number of actions."""
        # Create many actions
        actions = []
        for i in range(50):
            action = RiskAction.objects.create(
                risk=self.risk,
                title=f'Performance Action {i}',
                action_type='mitigation',
                assigned_to=self.user1 if i % 2 == 0 else self.user2,
                due_date=date.today() + timedelta(days=i % 10),
                status='pending'
            )
            actions.append(action)
        
        with patch('risk.notifications.RiskActionReminderService.send_individual_reminder') as mock_send:
            mock_send.return_value = True
            
            # Measure execution time
            start_time = timezone.now()
            result = send_risk_action_due_reminders.apply()
            end_time = timezone.now()
            
            execution_time = (end_time - start_time).total_seconds()
            
            self.assertTrue(result.successful())
            # Should complete within reasonable time (adjust threshold as needed)
            self.assertLess(execution_time, 10.0)  # 10 seconds max
            
            # Should process all eligible reminders
            self.assertGreater(mock_send.call_count, 0)