from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.messages.storage.fallback import FallbackStorage
from django_tenants.test.cases import TenantTestCase
from unittest.mock import Mock, patch

from ..models import (
    Risk,
    RiskCategory,
    RiskAction,
    RiskActionNote,
    RiskActionEvidence,
    RiskActionReminderConfiguration,
)
from ..admin import (
    RiskActionAdmin,
    RiskActionNoteAdmin,
    RiskActionEvidenceAdmin,
    RiskActionReminderConfigurationAdmin,
)

User = get_user_model()


class MockRequest:
    """Mock request object for admin testing."""

    def __init__(self, user=None):
        self.user = user or Mock()
        self.session = {}
        self.GET = {}
        self._messages = FallbackStorage(self)

    def build_absolute_uri(self, location=None):
        return f"http://example.com{location or ''}"


class RiskActionAdminTest(TestCase):
    """Test cases for RiskActionAdmin."""

    def setUp(self):
        self.site = AdminSite()
        self.admin = RiskActionAdmin(RiskAction, self.site)

        self.user = User.objects.create_user(
            username="admin_user", email="admin@example.com", password="adminpass123", is_staff=True
        )
        self.assignee = User.objects.create_user(
            username="assignee", email="assignee@example.com", password="testpass123"
        )

        self.category = RiskCategory.objects.create(name="Test Category")
        self.risk = Risk.objects.create(
            title="Test Risk",
            category=self.category,
            risk_owner=self.user,
            impact=4,
            likelihood=3,
            risk_level="high",
        )

        self.action = RiskAction.objects.create(
            risk=self.risk,
            title="Test Action",
            description="Test action for admin testing",
            action_type="mitigation",
            priority="high",
            assigned_to=self.assignee,
            due_date=date.today() + timedelta(days=14),
            status="in_progress",
            progress_percentage=35,
        )

    def test_list_display_fields(self):
        """Test that list display includes all expected fields."""
        expected_fields = [
            "action_id",
            "title",
            "risk_display",
            "priority_colored",
            "status_colored",
            "progress_bar",
            "assigned_to_display",
            "due_date_display",
            "created_at",
        ]

        self.assertEqual(list(self.admin.list_display), expected_fields)

    def test_list_filter_fields(self):
        """Test that list filters include all expected fields."""
        expected_filters = [
            "status",
            "priority",
            "action_type",
            ("assigned_to", self.admin.list_filter[3][1]),
            ("risk", self.admin.list_filter[4][1]),
            "due_date",
            "start_date",
            "completed_date",
            "created_at",
        ]

        self.assertEqual(list(self.admin.list_filter), expected_filters)

    def test_search_fields(self):
        """Test that search fields are properly configured."""
        expected_search = [
            "action_id",
            "title",
            "description",
            "risk__risk_id",
            "risk__title",
        ]

        self.assertEqual(list(self.admin.search_fields), expected_search)

    def test_risk_link_method(self):
        """Test the risk_link method returns proper HTML link."""
        request = MockRequest(self.user)

        link_html = self.admin.risk_display(self.action)

        self.assertIn(self.risk.risk_id, link_html)
        self.assertIn("<a href=", link_html)
        self.assertIn("href=", link_html)

    def test_progress_bar_method(self):
        """Test the progress_bar method returns proper HTML."""
        progress_html = self.admin.progress_bar(self.action)

        self.assertIn("35%", progress_html)
        self.assertIn("width: 35%", progress_html)
        self.assertIn("background-color: #f59e0b", progress_html)  # Orange for medium progress

        # Test different progress levels
        self.action.progress_percentage = 75
        progress_html = self.admin.progress_bar(self.action)
        self.assertIn("background-color: #10b981", progress_html)  # Green for high progress

        self.action.progress_percentage = 15
        progress_html = self.admin.progress_bar(self.action)
        self.assertIn("background-color: #ef4444", progress_html)  # Red for low progress

    def test_days_until_due_display_method(self):
        """Test the days_until_due_display method with different scenarios."""
        # Future due date
        future_action = RiskAction.objects.create(
            risk=self.risk,
            title="Future Action",
            action_type="mitigation",
            assigned_to=self.assignee,
            due_date=date.today() + timedelta(days=7),
        )

        display = self.admin.days_until_due_display(future_action)
        self.assertEqual(display, "7 days remaining")

        # Overdue action
        overdue_action = RiskAction.objects.create(
            risk=self.risk,
            title="Overdue Action",
            action_type="mitigation",
            assigned_to=self.assignee,
            due_date=date.today() - timedelta(days=3),
        )

        display = self.admin.days_until_due_display(overdue_action)
        self.assertIn("3 days overdue", display)
        self.assertIn("color: #DC2626", display)  # Red for overdue

        # Due today
        today_action = RiskAction.objects.create(
            risk=self.risk,
            title="Today Action",
            action_type="mitigation",
            assigned_to=self.assignee,
            due_date=date.today(),
        )

        display = self.admin.days_until_due_display(today_action)
        self.assertIn("Due today", display)
        self.assertIn("color: #F59E0B", display)  # Orange for due today

    def test_get_status_display_method(self):
        """Test the get_status_display method returns colored status."""
        # Test different statuses
        test_cases = [
            ("pending", "#6B7280"),
            ("in_progress", "#3B82F6"),
            ("completed", "#10B981"),
            ("cancelled", "#EF4444"),
        ]

        for status, expected_color in test_cases:
            self.action.status = status
            status_html = self.admin.status_colored(self.action)

            self.assertIn(expected_color, status_html)
            self.assertIn(status.replace("_", " ").title(), status_html)

    def test_get_priority_display_method(self):
        """Test the get_priority_display method returns colored priority."""
        test_cases = [
            ("low", "#10B981"),
            ("medium", "#F59E0B"),
            ("high", "#EF4444"),
            ("critical", "#DC2626"),
        ]

        for priority, expected_color in test_cases:
            self.action.priority = priority
            priority_html = self.admin.priority_colored(self.action)

            self.assertIn(expected_color, priority_html)
            self.assertIn(priority.title(), priority_html)

    def test_fieldsets_configuration(self):
        """Test that fieldsets are properly configured."""
        fieldsets = self.admin.get_fieldsets(MockRequest(self.user))

        # Check that we have the expected number of fieldsets
        self.assertEqual(len(fieldsets), 6)

        # Check fieldset titles
        fieldset_titles = [fs[0] for fs in fieldsets]
        expected_titles = [
            "Action Information",
            "Assignment & Priority",
            "Scheduling",
            "Cost & Effort",
            "Requirements",
            "Metadata",
        ]
        self.assertEqual(fieldset_titles, expected_titles)

    @patch("risk.notifications.RiskActionReminderService.send_assignment_notification")
    def test_save_model_triggers_notification(self, mock_notify):
        """Test that saving an action triggers appropriate notifications."""
        request = MockRequest(self.user)

        # Test creating new action
        new_action = RiskAction(
            risk=self.risk,
            title="New Test Action",
            action_type="mitigation",
            assigned_to=self.assignee,
            due_date=date.today() + timedelta(days=20),
        )

        self.admin.save_model(request, new_action, None, False)

        # Should trigger assignment notification for new action
        mock_notify.assert_called_once_with(new_action, new_action.assigned_to, request.user)

    def test_bulk_actions(self):
        """Test custom bulk actions."""
        actions = self.admin.get_actions(MockRequest(self.user))

        # Check that custom actions are present
        self.assertIn("mark_as_completed", actions)
        self.assertIn("mark_as_deferred", actions)
        self.assertIn("send_reminder_notifications", actions)

    @patch("risk.tasks.send_immediate_risk_action_reminder.delay")
    def test_send_reminder_notifications_action(self, mock_send_reminder):
        """Test the send reminder emails bulk action."""
        request = MockRequest(self.user)
        mock_send_reminder.return_value = True

        queryset = RiskAction.objects.filter(id=self.action.id)

        result = self.admin.send_reminder_notifications(request, queryset)

        self.assertIsNone(result)  # Bulk actions return None on success
        mock_send_reminder.assert_called_once_with(
            self.action.id, self.assignee.id, "advance_warning"
        )

    def test_mark_as_completed_action(self):
        """Test the mark as completed bulk action."""
        request = MockRequest(self.user)

        queryset = RiskAction.objects.filter(id=self.action.id)

        result = self.admin.mark_as_completed(request, queryset)

        self.action.refresh_from_db()
        self.assertEqual(self.action.status, "completed")
        self.assertEqual(self.action.progress_percentage, 100)

    def test_mark_as_cancelled_action(self):
        """Test the mark as cancelled bulk action."""
        request = MockRequest(self.user)

        queryset = RiskAction.objects.filter(id=self.action.id)

        result = self.admin.mark_as_deferred(request, queryset)

        self.action.refresh_from_db()
        self.assertEqual(self.action.status, "deferred")


class RiskActionNoteAdminTest(TestCase):
    """Test cases for RiskActionNoteAdmin."""

    def setUp(self):
        self.site = AdminSite()
        self.admin = RiskActionNoteAdmin(RiskActionNote, self.site)

        self.user = User.objects.create_user(
            username="test_user", email="test@example.com", password="testpass123"
        )

        self.category = RiskCategory.objects.create(name="Test")
        self.risk = Risk.objects.create(
            title="Test Risk", category=self.category, risk_owner=self.user, impact=3, likelihood=3
        )
        self.action = RiskAction.objects.create(
            risk=self.risk,
            title="Test Action",
            action_type="mitigation",
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=30),
        )

        self.note = RiskActionNote.objects.create(
            action=self.action, note="Test note content", created_by=self.user
        )

    def test_list_display_fields(self):
        """Test list display configuration."""
        expected_fields = [
            "action_display",
            "note_type",
            "note_preview",
            "progress_display",
            "created_by_display",
            "created_at",
        ]
        self.assertEqual(list(self.admin.list_display), expected_fields)

    def test_note_preview_method(self):
        """Test the note_preview method truncates long notes."""
        # Test short note
        preview = self.admin.note_preview(self.note)
        self.assertEqual(preview, "Test note content")

        # Test long note
        long_note = RiskActionNote.objects.create(
            action=self.action,
            note="A" * 200,  # 200 character note
            created_by=self.user,
        )

        preview = self.admin.note_preview(long_note)
        self.assertEqual(len(preview), 103)  # 100 chars + '...'
        self.assertTrue(preview.endswith("..."))

    def test_created_at_is_read_only(self):
        """Test that the admin protects the note timestamp."""
        self.assertIn("created_at", self.admin.readonly_fields)


class RiskActionEvidenceAdminTest(TestCase):
    """Test cases for RiskActionEvidenceAdmin."""

    def setUp(self):
        self.site = AdminSite()
        self.admin = RiskActionEvidenceAdmin(RiskActionEvidence, self.site)

        self.user = User.objects.create_user(
            username="test_user", email="test@example.com", password="testpass123"
        )

        self.category = RiskCategory.objects.create(name="Test")
        self.risk = Risk.objects.create(
            title="Test Risk", category=self.category, risk_owner=self.user, impact=3, likelihood=3
        )
        self.action = RiskAction.objects.create(
            risk=self.risk,
            title="Test Action",
            action_type="mitigation",
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=30),
        )

        self.evidence = RiskActionEvidence.objects.create(
            action=self.action,
            title="Test Evidence",
            evidence_type="document",
            description="Evidence description",
            uploaded_by=self.user,
        )

    def test_list_display_fields(self):
        """Test list display configuration."""
        expected_fields = [
            "title",
            "action_display",
            "evidence_type",
            "validation_status",
            "uploaded_by_display",
            "evidence_date",
        ]
        self.assertEqual(list(self.admin.list_display), expected_fields)

    def test_display_methods(self):
        """Test evidence display methods for an unvalidated item."""
        link = self.admin.action_display(self.evidence)
        self.assertIn(self.action.action_id, link)

        link = self.admin.uploaded_by_display(self.evidence)
        self.assertEqual(link, self.user.username)

        link = self.admin.validation_status(self.evidence)
        self.assertIn("Pending", link)

    def test_uploaded_by_is_read_only(self):
        """Test that the uploader is controlled by the admin configuration."""
        self.assertIn("uploaded_by", self.admin.readonly_fields)


class RiskActionReminderConfigurationAdminTest(TestCase):
    """Test cases for RiskActionReminderConfigurationAdmin."""

    def setUp(self):
        self.site = AdminSite()
        self.admin = RiskActionReminderConfigurationAdmin(
            RiskActionReminderConfiguration, self.site
        )

        self.user = User.objects.create_user(
            username="test_user", email="test@example.com", password="testpass123"
        )

        self.config = RiskActionReminderConfiguration.objects.create(user=self.user)

    def test_list_display_fields(self):
        """Test list display configuration."""
        expected_fields = [
            "user_display",
            "enable_reminders",
            "advance_warning_days",
            "reminder_frequency",
            "email_notifications",
            "weekly_digest_enabled",
            "updated_at",
        ]
        self.assertEqual(list(self.admin.list_display), expected_fields)

    def test_list_filter_fields(self):
        """Test list filter configuration."""
        expected_filters = [
            "enable_reminders",
            "email_notifications",
            "reminder_frequency",
            "weekly_digest_enabled",
            "overdue_reminders",
            "silence_completed",
            "updated_at",
        ]
        self.assertEqual(list(self.admin.list_filter), expected_filters)

    def test_search_fields(self):
        """Test search fields configuration."""
        expected_search = ["user__username", "user__email", "user__first_name", "user__last_name"]
        self.assertEqual(list(self.admin.search_fields), expected_search)


class AdminIntegrationTest(TenantTestCase):
    """Integration tests for admin interface."""

    def setUp(self):
        super().setUp()
        self.client.defaults["HTTP_HOST"] = self.domain.domain
        self.user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        self.client.force_login(self.user)

        self.category = RiskCategory.objects.create(name="Test")
        self.risk = Risk.objects.create(
            title="Test Risk", category=self.category, risk_owner=self.user, impact=3, likelihood=3
        )

    def test_risk_action_admin_changelist_view(self):
        """Test that risk action changelist loads successfully."""
        RiskAction.objects.create(
            risk=self.risk,
            title="Test Action",
            action_type="mitigation",
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=30),
        )

        response = self.client.get(reverse("admin:risk_riskaction_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Action")

    def test_risk_action_admin_add_view(self):
        """Test that risk action add form loads successfully."""
        response = self.client.get(reverse("admin:risk_riskaction_add"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Risk")
        self.assertContains(response, "Title")
        self.assertContains(response, "Action type")

    def test_risk_action_admin_change_view(self):
        """Test that risk action change form loads successfully."""
        action = RiskAction.objects.create(
            risk=self.risk,
            title="Test Action",
            action_type="mitigation",
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=30),
        )

        response = self.client.get(reverse("admin:risk_riskaction_change", args=[action.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Action")
        self.assertContains(response, action.action_id)
