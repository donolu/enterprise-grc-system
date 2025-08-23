from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.admin import ModelAdmin
from django.http import HttpRequest
from django.contrib.messages.storage.fallback import FallbackStorage
from unittest.mock import Mock, patch

from ..models import (
    Risk, RiskCategory, RiskAction, RiskActionNote, 
    RiskActionEvidence, RiskActionReminderConfiguration
)
from ..admin import (
    RiskActionAdmin, RiskActionNoteAdmin, RiskActionEvidenceAdmin,
    RiskActionReminderConfigurationAdmin
)

User = get_user_model()


class MockRequest:
    """Mock request object for admin testing."""
    def __init__(self, user=None):
        self.user = user or Mock()
        self._messages = FallbackStorage(self)
    
    def build_absolute_uri(self, location=None):
        return f'http://example.com{location or ""}'


class RiskActionAdminTest(TestCase):
    """Test cases for RiskActionAdmin."""
    
    def setUp(self):
        self.site = AdminSite()
        self.admin = RiskActionAdmin(RiskAction, self.site)
        
        self.user = User.objects.create_user(
            username='admin_user',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True
        )
        self.assignee = User.objects.create_user(
            username='assignee',
            email='assignee@example.com',
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
            impact=4,
            likelihood=3,
            risk_level='high'
        )
        
        self.action = RiskAction.objects.create(
            risk=self.risk,
            title='Test Action',
            description='Test action for admin testing',
            action_type='mitigation',
            priority='high',
            assigned_to=self.assignee,
            due_date=date.today() + timedelta(days=14),
            status='in_progress',
            progress_percentage=35
        )
    
    def test_list_display_fields(self):
        """Test that list display includes all expected fields."""
        expected_fields = [
            'action_id', 'title', 'risk_link', 'action_type', 'priority',
            'assigned_to', 'status', 'progress_bar', 'due_date', 'days_until_due_display'
        ]
        
        self.assertEqual(list(self.admin.list_display), expected_fields)
    
    def test_list_filter_fields(self):
        """Test that list filters include all expected fields."""
        expected_filters = [
            'status', 'priority', 'action_type', 'due_date',
            'assigned_to', 'risk__risk_level', 'created_at'
        ]
        
        self.assertEqual(list(self.admin.list_filter), expected_filters)
    
    def test_search_fields(self):
        """Test that search fields are properly configured."""
        expected_search = [
            'action_id', 'title', 'description', 'risk__risk_id',
            'risk__title', 'assigned_to__username', 'assigned_to__email'
        ]
        
        self.assertEqual(list(self.admin.search_fields), expected_search)
    
    def test_risk_link_method(self):
        """Test the risk_link method returns proper HTML link."""
        request = MockRequest(self.user)
        
        link_html = self.admin.risk_link(self.action)
        
        self.assertIn(self.risk.risk_id, link_html)
        self.assertIn(self.risk.title, link_html)
        self.assertIn('<a href=', link_html)
        self.assertIn('target="_blank"', link_html)
    
    def test_progress_bar_method(self):
        """Test the progress_bar method returns proper HTML."""
        progress_html = self.admin.progress_bar(self.action)
        
        self.assertIn('35%', progress_html)
        self.assertIn('width: 35%', progress_html)
        self.assertIn('background-color: #f59e0b', progress_html)  # Orange for medium progress
        
        # Test different progress levels
        self.action.progress_percentage = 75
        progress_html = self.admin.progress_bar(self.action)
        self.assertIn('background-color: #10b981', progress_html)  # Green for high progress
        
        self.action.progress_percentage = 15
        progress_html = self.admin.progress_bar(self.action)
        self.assertIn('background-color: #ef4444', progress_html)  # Red for low progress
    
    def test_days_until_due_display_method(self):
        """Test the days_until_due_display method with different scenarios."""
        # Future due date
        future_action = RiskAction.objects.create(
            risk=self.risk,
            title='Future Action',
            action_type='mitigation',
            assigned_to=self.assignee,
            due_date=date.today() + timedelta(days=7)
        )
        
        display = self.admin.days_until_due_display(future_action)
        self.assertIn('7 days', display)
        self.assertIn('color: #059669', display)  # Green for future
        
        # Overdue action
        overdue_action = RiskAction.objects.create(
            risk=self.risk,
            title='Overdue Action',
            action_type='mitigation',
            assigned_to=self.assignee,
            due_date=date.today() - timedelta(days=3)
        )
        
        display = self.admin.days_until_due_display(overdue_action)
        self.assertIn('3 days overdue', display)
        self.assertIn('color: #dc2626', display)  # Red for overdue
        
        # Due today
        today_action = RiskAction.objects.create(
            risk=self.risk,
            title='Today Action',
            action_type='mitigation',
            assigned_to=self.assignee,
            due_date=date.today()
        )
        
        display = self.admin.days_until_due_display(today_action)
        self.assertIn('Due today', display)
        self.assertIn('color: #f59e0b', display)  # Orange for due today
    
    def test_get_status_display_method(self):
        """Test the get_status_display method returns colored status."""
        # Test different statuses
        test_cases = [
            ('pending', '#6b7280'),     # Gray
            ('in_progress', '#2563eb'), # Blue
            ('completed', '#059669'),   # Green
            ('cancelled', '#dc2626')    # Red
        ]
        
        for status, expected_color in test_cases:
            self.action.status = status
            status_html = self.admin.get_status_display(self.action)
            
            self.assertIn(expected_color, status_html)
            self.assertIn(status.replace('_', ' ').title(), status_html)
    
    def test_get_priority_display_method(self):
        """Test the get_priority_display method returns colored priority."""
        test_cases = [
            ('low', '#6b7280'),      # Gray
            ('medium', '#f59e0b'),   # Orange
            ('high', '#dc2626'),     # Red
            ('critical', '#991b1b')  # Dark red
        ]
        
        for priority, expected_color in test_cases:
            self.action.priority = priority
            priority_html = self.admin.get_priority_display(self.action)
            
            self.assertIn(expected_color, priority_html)
            self.assertIn(priority.title(), priority_html)
    
    def test_fieldsets_configuration(self):
        """Test that fieldsets are properly configured."""
        fieldsets = self.admin.get_fieldsets(MockRequest(self.user))
        
        # Check that we have the expected number of fieldsets
        self.assertEqual(len(fieldsets), 4)
        
        # Check fieldset titles
        fieldset_titles = [fs[0] for fs in fieldsets]
        expected_titles = ['Basic Information', 'Assignment & Dates', 'Progress & Status', 'Additional Information']
        self.assertEqual(fieldset_titles, expected_titles)
    
    @patch('risk.notifications.RiskActionNotificationService.notify_assignment')
    def test_save_model_triggers_notification(self, mock_notify):
        """Test that saving an action triggers appropriate notifications."""
        request = MockRequest(self.user)
        
        # Test creating new action
        new_action = RiskAction(
            risk=self.risk,
            title='New Test Action',
            action_type='mitigation',
            assigned_to=self.assignee,
            due_date=date.today() + timedelta(days=20)
        )
        
        self.admin.save_model(request, new_action, None, True)
        
        # Should trigger assignment notification for new action
        mock_notify.assert_called_once_with(new_action, request.user)
    
    def test_bulk_actions(self):
        """Test custom bulk actions."""
        actions = self.admin.get_actions(MockRequest(self.user))
        
        # Check that custom actions are present
        self.assertIn('mark_as_completed', actions)
        self.assertIn('mark_as_cancelled', actions)
        self.assertIn('send_reminder_emails', actions)
    
    @patch('risk.notifications.RiskActionReminderService.send_individual_reminder')
    def test_send_reminder_emails_action(self, mock_send_reminder):
        """Test the send reminder emails bulk action."""
        request = MockRequest(self.user)
        mock_send_reminder.return_value = True
        
        queryset = RiskAction.objects.filter(id=self.action.id)
        
        result = self.admin.send_reminder_emails(request, queryset)
        
        self.assertIsNone(result)  # Bulk actions return None on success
        mock_send_reminder.assert_called_once()
    
    def test_mark_as_completed_action(self):
        """Test the mark as completed bulk action."""
        request = MockRequest(self.user)
        
        queryset = RiskAction.objects.filter(id=self.action.id)
        
        result = self.admin.mark_as_completed(request, queryset)
        
        self.action.refresh_from_db()
        self.assertEqual(self.action.status, 'completed')
        self.assertEqual(self.action.progress_percentage, 100)
        self.assertIsNotNone(self.action.completed_date)
    
    def test_mark_as_cancelled_action(self):
        """Test the mark as cancelled bulk action."""
        request = MockRequest(self.user)
        
        queryset = RiskAction.objects.filter(id=self.action.id)
        
        result = self.admin.mark_as_cancelled(request, queryset)
        
        self.action.refresh_from_db()
        self.assertEqual(self.action.status, 'cancelled')


class RiskActionNoteAdminTest(TestCase):
    """Test cases for RiskActionNoteAdmin."""
    
    def setUp(self):
        self.site = AdminSite()
        self.admin = RiskActionNoteAdmin(RiskActionNote, self.site)
        
        self.user = User.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='testpass123'
        )
        
        self.category = RiskCategory.objects.create(name='Test', code='TEST')
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
        
        self.note = RiskActionNote.objects.create(
            action=self.action,
            note='Test note content',
            created_by=self.user
        )
    
    def test_list_display_fields(self):
        """Test list display configuration."""
        expected_fields = ['action', 'note_preview', 'created_by', 'created_at']
        self.assertEqual(list(self.admin.list_display), expected_fields)
    
    def test_note_preview_method(self):
        """Test the note_preview method truncates long notes."""
        # Test short note
        preview = self.admin.note_preview(self.note)
        self.assertEqual(preview, 'Test note content')
        
        # Test long note
        long_note = RiskActionNote.objects.create(
            action=self.action,
            note='A' * 200,  # 200 character note
            created_by=self.user
        )
        
        preview = self.admin.note_preview(long_note)
        self.assertEqual(len(preview), 103)  # 100 chars + '...'
        self.assertTrue(preview.endswith('...'))
    
    def test_save_model_sets_created_by(self):
        """Test that save_model automatically sets created_by."""
        request = MockRequest(self.user)
        
        new_note = RiskActionNote(
            action=self.action,
            note='New note without created_by set'
        )
        
        self.admin.save_model(request, new_note, None, True)
        
        self.assertEqual(new_note.created_by, self.user)


class RiskActionEvidenceAdminTest(TestCase):
    """Test cases for RiskActionEvidenceAdmin."""
    
    def setUp(self):
        self.site = AdminSite()
        self.admin = RiskActionEvidenceAdmin(RiskActionEvidence, self.site)
        
        self.user = User.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='testpass123'
        )
        
        self.category = RiskCategory.objects.create(name='Test', code='TEST')
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
        
        self.evidence = RiskActionEvidence.objects.create(
            action=self.action,
            title='Test Evidence',
            evidence_type='document',
            description='Evidence description',
            uploaded_by=self.user
        )
    
    def test_list_display_fields(self):
        """Test list display configuration."""
        expected_fields = [
            'title', 'action', 'evidence_type', 'uploaded_by',
            'created_at', 'is_validated', 'file_link'
        ]
        self.assertEqual(list(self.admin.list_display), expected_fields)
    
    def test_file_link_method_with_file(self):
        """Test file_link method when evidence has file."""
        # This test would need actual file upload in a real scenario
        # For now, test the case where there's no file
        link = self.admin.file_link(self.evidence)
        self.assertEqual(link, '-')
    
    def test_save_model_sets_uploaded_by(self):
        """Test that save_model automatically sets uploaded_by."""
        request = MockRequest(self.user)
        
        new_evidence = RiskActionEvidence(
            action=self.action,
            title='New Evidence',
            evidence_type='screenshot'
        )
        
        with patch('risk.notifications.RiskActionNotificationService.notify_evidence_uploaded') as mock_notify:
            self.admin.save_model(request, new_evidence, None, True)
            
            self.assertEqual(new_evidence.uploaded_by, self.user)
            # Should trigger evidence notification for new evidence
            mock_notify.assert_called_once_with(new_evidence, request.user)


class RiskActionReminderConfigurationAdminTest(TestCase):
    """Test cases for RiskActionReminderConfigurationAdmin."""
    
    def setUp(self):
        self.site = AdminSite()
        self.admin = RiskActionReminderConfigurationAdmin(RiskActionReminderConfiguration, self.site)
        
        self.user = User.objects.create_user(
            username='test_user',
            email='test@example.com',
            password='testpass123'
        )
        
        self.config = RiskActionReminderConfiguration.objects.create(
            user=self.user,
            enabled=True,
            send_due_reminders=True,
            reminder_days_before=7
        )
    
    def test_list_display_fields(self):
        """Test list display configuration."""
        expected_fields = [
            'user', 'enabled', 'send_assignment_notifications',
            'send_due_reminders', 'send_overdue_reminders',
            'send_weekly_digest', 'reminder_days_before'
        ]
        self.assertEqual(list(self.admin.list_display), expected_fields)
    
    def test_list_filter_fields(self):
        """Test list filter configuration."""
        expected_filters = [
            'enabled', 'send_assignment_notifications', 'send_due_reminders',
            'send_overdue_reminders', 'send_weekly_digest'
        ]
        self.assertEqual(list(self.admin.list_filter), expected_filters)
    
    def test_search_fields(self):
        """Test search fields configuration."""
        expected_search = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
        self.assertEqual(list(self.admin.search_fields), expected_search)


class AdminIntegrationTest(TestCase):
    """Integration tests for admin interface."""
    
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.client.force_login(self.user)
        
        self.category = RiskCategory.objects.create(name='Test', code='TEST')
        self.risk = Risk.objects.create(
            title='Test Risk',
            category=self.category,
            risk_owner=self.user,
            impact=3,
            likelihood=3
        )
    
    def test_risk_action_admin_changelist_view(self):
        """Test that risk action changelist loads successfully."""
        RiskAction.objects.create(
            risk=self.risk,
            title='Test Action',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=30)
        )
        
        response = self.client.get('/admin/risk/riskaction/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Action')
    
    def test_risk_action_admin_add_view(self):
        """Test that risk action add form loads successfully."""
        response = self.client.get('/admin/risk/riskaction/add/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Risk')
        self.assertContains(response, 'Title')
        self.assertContains(response, 'Action type')
    
    def test_risk_action_admin_change_view(self):
        """Test that risk action change form loads successfully."""
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Test Action',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=30)
        )
        
        response = self.client.get(f'/admin/risk/riskaction/{action.id}/change/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Action')
        self.assertContains(response, action.action_id)