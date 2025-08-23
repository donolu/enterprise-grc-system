import json
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock

from ..models import (
    Risk, RiskCategory, RiskAction, RiskActionNote, 
    RiskActionEvidence, RiskActionReminderConfiguration, RiskActionReminderLog
)
from ..notifications import RiskActionReminderService, RiskActionNotificationService
from ..tasks import send_risk_action_due_reminders, send_risk_action_weekly_digests

User = get_user_model()


class RiskActionModelTest(TestCase):
    """Test cases for RiskAction model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = RiskCategory.objects.create(
            name='Test Category',
            code='TEST',
            description='Test category'
        )
        self.risk = Risk.objects.create(
            title='Test Risk',
            description='Test risk description',
            category=self.category,
            risk_owner=self.user,
            impact=4,
            likelihood=3,
            risk_level='high',
            status='assessed'
        )
    
    def test_risk_action_creation(self):
        """Test creating a risk action with automatic ID generation."""
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Test Action',
            description='Test action description',
            action_type='mitigation',
            priority='high',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=30)
        )
        
        self.assertIsNotNone(action.action_id)
        self.assertTrue(action.action_id.startswith(f'RA-{timezone.now().year}'))
        self.assertEqual(action.status, 'pending')
        self.assertEqual(action.progress_percentage, 0)
        self.assertIsNotNone(action.created_at)
    
    def test_risk_action_id_generation(self):
        """Test that action IDs are generated sequentially."""
        action1 = RiskAction.objects.create(
            risk=self.risk,
            title='Action 1',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=30)
        )
        action2 = RiskAction.objects.create(
            risk=self.risk,
            title='Action 2',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=30)
        )
        
        # Extract sequence numbers
        seq1 = int(action1.action_id.split('-')[-1])
        seq2 = int(action2.action_id.split('-')[-1])
        
        self.assertEqual(seq2, seq1 + 1)
    
    def test_risk_action_properties(self):
        """Test calculated properties of risk action."""
        due_date = date.today() + timedelta(days=5)
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Test Action',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=due_date
        )
        
        self.assertEqual(action.days_until_due, 5)
        self.assertFalse(action.is_overdue)
        
        # Test overdue action
        overdue_action = RiskAction.objects.create(
            risk=self.risk,
            title='Overdue Action',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() - timedelta(days=1)
        )
        
        self.assertTrue(overdue_action.is_overdue)
        self.assertEqual(overdue_action.days_until_due, -1)
    
    def test_risk_action_completion(self):
        """Test action completion logic."""
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Test Action',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=30)
        )
        
        action.status = 'completed'
        action.progress_percentage = 100
        action.save()
        
        self.assertIsNotNone(action.completed_date)
        self.assertEqual(action.status, 'completed')


class RiskActionNoteModelTest(TestCase):
    """Test cases for RiskActionNote model."""
    
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
            due_date=date.today() + timedelta(days=30)
        )
    
    def test_note_creation(self):
        """Test creating action notes."""
        note = RiskActionNote.objects.create(
            action=self.action,
            note='Test note content',
            created_by=self.user
        )
        
        self.assertEqual(note.action, self.action)
        self.assertEqual(note.note, 'Test note content')
        self.assertEqual(note.created_by, self.user)
        self.assertIsNotNone(note.created_at)


class RiskActionEvidenceModelTest(TestCase):
    """Test cases for RiskActionEvidence model."""
    
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
            due_date=date.today() + timedelta(days=30)
        )
    
    def test_evidence_creation(self):
        """Test creating action evidence."""
        evidence = RiskActionEvidence.objects.create(
            action=self.action,
            title='Test Evidence',
            evidence_type='document',
            description='Test evidence description',
            uploaded_by=self.user
        )
        
        self.assertEqual(evidence.action, self.action)
        self.assertEqual(evidence.title, 'Test Evidence')
        self.assertEqual(evidence.evidence_type, 'document')
        self.assertEqual(evidence.uploaded_by, self.user)
        self.assertIsNotNone(evidence.created_at)


class RiskActionReminderConfigurationModelTest(TestCase):
    """Test cases for RiskActionReminderConfiguration model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_default_configuration(self):
        """Test default reminder configuration creation."""
        config = RiskActionReminderConfiguration.get_or_create_for_user(self.user)
        
        self.assertEqual(config.user, self.user)
        self.assertTrue(config.enabled)
        self.assertTrue(config.send_assignment_notifications)
        self.assertTrue(config.send_due_reminders)
        self.assertTrue(config.send_overdue_reminders)
        self.assertTrue(config.send_weekly_digest)
        self.assertEqual(config.reminder_days_before, 7)


class RiskActionAPITest(APITestCase):
    """Test cases for Risk Action API endpoints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
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
    
    def test_create_risk_action(self):
        """Test creating a risk action via API."""
        url = reverse('riskaction-list')
        data = {
            'risk': self.risk.id,
            'title': 'Test Action',
            'description': 'Test action description',
            'action_type': 'mitigation',
            'priority': 'high',
            'assigned_to': self.user.id,
            'due_date': (date.today() + timedelta(days=30)).isoformat()
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(RiskAction.objects.count(), 1)
        
        action = RiskAction.objects.first()
        self.assertEqual(action.title, 'Test Action')
        self.assertEqual(action.action_type, 'mitigation')
    
    def test_list_risk_actions(self):
        """Test listing risk actions via API."""
        RiskAction.objects.create(
            risk=self.risk,
            title='Action 1',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=30)
        )
        RiskAction.objects.create(
            risk=self.risk,
            title='Action 2',
            action_type='acceptance',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=15)
        )
        
        url = reverse('riskaction-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_update_action_status(self):
        """Test updating action status via API."""
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Test Action',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=30)
        )
        
        url = reverse('riskaction-update-status', kwargs={'pk': action.pk})
        data = {
            'status': 'in_progress',
            'progress_percentage': 25,
            'note': 'Started working on this action'
        }
        
        with patch('risk.notifications.RiskActionNotificationService.notify_status_change') as mock_notify:
            response = self.client.post(url, data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            mock_notify.assert_called_once()
        
        action.refresh_from_db()
        self.assertEqual(action.status, 'in_progress')
        self.assertEqual(action.progress_percentage, 25)
    
    def test_add_note_to_action(self):
        """Test adding a note to an action via API."""
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Test Action',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=30)
        )
        
        url = reverse('riskaction-add-note', kwargs={'pk': action.pk})
        data = {
            'note': 'This is a test note'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(RiskActionNote.objects.count(), 1)
        
        note = RiskActionNote.objects.first()
        self.assertEqual(note.note, 'This is a test note')
        self.assertEqual(note.created_by, self.user)
    
    def test_upload_evidence(self):
        """Test uploading evidence to an action via API."""
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Test Action',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=30)
        )
        
        # Create a simple test file
        test_file = SimpleUploadedFile(
            "test_evidence.txt",
            b"Test evidence content",
            content_type="text/plain"
        )
        
        url = reverse('riskaction-upload-evidence', kwargs={'pk': action.pk})
        data = {
            'title': 'Test Evidence',
            'evidence_type': 'document',
            'description': 'Test evidence description',
            'file': test_file
        }
        
        with patch('risk.notifications.RiskActionNotificationService.notify_evidence_uploaded') as mock_notify:
            response = self.client.post(url, data, format='multipart')
            
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            mock_notify.assert_called_once()
        
        self.assertEqual(RiskActionEvidence.objects.count(), 1)
        evidence = RiskActionEvidence.objects.first()
        self.assertEqual(evidence.title, 'Test Evidence')
        self.assertEqual(evidence.uploaded_by, self.user)


class RiskActionNotificationTest(TestCase):
    """Test cases for risk action notifications."""
    
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
    
    @patch('risk.notifications.send_mail')
    def test_assignment_notification(self, mock_send_mail):
        """Test assignment notification sending."""
        mock_send_mail.return_value = True
        
        RiskActionNotificationService.notify_assignment(self.action, self.user)
        
        mock_send_mail.assert_called_once()
        call_args = mock_send_mail.call_args
        self.assertIn('Risk Action Assignment', call_args[0][0])
        self.assertIn(self.user.email, call_args[0][3])
    
    @patch('risk.notifications.send_mail')
    def test_status_change_notification(self, mock_send_mail):
        """Test status change notification sending."""
        mock_send_mail.return_value = True
        
        RiskActionNotificationService.notify_status_change(
            self.action, 'pending', 'in_progress', self.user
        )
        
        mock_send_mail.assert_called_once()
        call_args = mock_send_mail.call_args
        self.assertIn('Risk Action Status Update', call_args[0][0])
    
    @patch('risk.notifications.send_mail')
    def test_reminder_notification(self, mock_send_mail):
        """Test reminder notification sending."""
        mock_send_mail.return_value = True
        
        RiskActionReminderService.send_individual_reminder(
            self.action, self.user, 'due_soon', 3
        )
        
        mock_send_mail.assert_called_once()
        call_args = mock_send_mail.call_args
        self.assertIn('Risk Action Reminder', call_args[0][0])


class RiskActionTaskTest(TestCase):
    """Test cases for risk action Celery tasks."""
    
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
    
    @patch('risk.notifications.RiskActionReminderService.send_individual_reminder')
    def test_due_reminders_task(self, mock_send_reminder):
        """Test the due reminders Celery task."""
        # Create actions with different due dates
        RiskAction.objects.create(
            risk=self.risk,
            title='Due Soon',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=3)
        )
        RiskAction.objects.create(
            risk=self.risk,
            title='Due Today',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today()
        )
        RiskAction.objects.create(
            risk=self.risk,
            title='Overdue',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() - timedelta(days=1)
        )
        
        # Run the task
        result = send_risk_action_due_reminders.apply()
        
        self.assertTrue(result.successful())
        # Should send reminders for all three actions
        self.assertEqual(mock_send_reminder.call_count, 3)
    
    @patch('risk.notifications.RiskActionNotificationService.send_weekly_digest')
    def test_weekly_digest_task(self, mock_send_digest):
        """Test the weekly digest Celery task."""
        # Create some actions for the user
        RiskAction.objects.create(
            risk=self.risk,
            title='Action 1',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=7)
        )
        
        result = send_risk_action_weekly_digests.apply()
        
        self.assertTrue(result.successful())
        mock_send_digest.assert_called()


class RiskActionFilterTest(TestCase):
    """Test cases for risk action filtering."""
    
    def setUp(self):
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
        self.category = RiskCategory.objects.create(
            name='Test Category',
            code='TEST'
        )
        self.risk = Risk.objects.create(
            title='Test Risk',
            category=self.category,
            risk_owner=self.user1,
            impact=3,
            likelihood=3
        )
        
        # Create test actions
        self.overdue_action = RiskAction.objects.create(
            risk=self.risk,
            title='Overdue Action',
            action_type='mitigation',
            priority='high',
            assigned_to=self.user1,
            due_date=date.today() - timedelta(days=5),
            status='in_progress'
        )
        
        self.due_soon_action = RiskAction.objects.create(
            risk=self.risk,
            title='Due Soon Action',
            action_type='acceptance',
            priority='medium',
            assigned_to=self.user2,
            due_date=date.today() + timedelta(days=3),
            status='pending'
        )
        
        self.future_action = RiskAction.objects.create(
            risk=self.risk,
            title='Future Action',
            action_type='mitigation',
            priority='low',
            assigned_to=self.user1,
            due_date=date.today() + timedelta(days=30),
            status='completed'
        )
    
    def test_overdue_filter(self):
        """Test filtering overdue actions."""
        from ..filters import RiskActionFilter
        
        # Mock request object
        mock_request = MagicMock()
        mock_request.user = self.user1
        
        filter_instance = RiskActionFilter(
            data={'overdue': True},
            queryset=RiskAction.objects.all(),
            request=mock_request
        )
        
        filtered_actions = filter_instance.qs
        
        self.assertEqual(filtered_actions.count(), 1)
        self.assertEqual(filtered_actions.first(), self.overdue_action)
    
    def test_due_soon_filter(self):
        """Test filtering actions due soon."""
        from ..filters import RiskActionFilter
        
        mock_request = MagicMock()
        mock_request.user = self.user1
        
        filter_instance = RiskActionFilter(
            data={'due_soon': True},
            queryset=RiskAction.objects.all(),
            request=mock_request
        )
        
        filtered_actions = filter_instance.qs
        
        self.assertEqual(filtered_actions.count(), 1)
        self.assertEqual(filtered_actions.first(), self.due_soon_action)
    
    def test_assigned_to_me_filter(self):
        """Test filtering actions assigned to current user."""
        from ..filters import RiskActionFilter
        
        mock_request = MagicMock()
        mock_request.user = self.user1
        mock_request.user.is_authenticated = True
        
        filter_instance = RiskActionFilter(
            data={'assigned_to_me': True},
            queryset=RiskAction.objects.all(),
            request=mock_request
        )
        
        filtered_actions = filter_instance.qs
        
        self.assertEqual(filtered_actions.count(), 2)
        assigned_users = [action.assigned_to for action in filtered_actions]
        self.assertTrue(all(user == self.user1 for user in assigned_users))
    
    def test_high_priority_filter(self):
        """Test filtering high priority actions."""
        from ..filters import RiskActionFilter
        
        mock_request = MagicMock()
        
        filter_instance = RiskActionFilter(
            data={'high_priority': True},
            queryset=RiskAction.objects.all(),
            request=mock_request
        )
        
        filtered_actions = filter_instance.qs
        
        self.assertEqual(filtered_actions.count(), 1)
        self.assertEqual(filtered_actions.first().priority, 'high')
    
    def test_search_filter(self):
        """Test text search across multiple fields."""
        from ..filters import RiskActionFilter
        
        mock_request = MagicMock()
        
        filter_instance = RiskActionFilter(
            data={'search': 'Overdue'},
            queryset=RiskAction.objects.all(),
            request=mock_request
        )
        
        filtered_actions = filter_instance.qs
        
        self.assertEqual(filtered_actions.count(), 1)
        self.assertIn('Overdue', filtered_actions.first().title)