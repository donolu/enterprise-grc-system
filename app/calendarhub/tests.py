from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from django_tenants.utils import tenant_context

from assets.models import Asset
from calendarhub.models import CalendarAuditLog, CalendarEvent, CalendarNotificationPreference, CalendarReminderLog
from calendarhub.services import list_calendar_events, send_due_reminders
from calendarhub.tasks import send_calendar_deadline_reminders
from catalogs.models import Clause, Control, ControlAssessment, Framework
from policies.models import Policy, PolicyCategory
from risk.models import Risk, RiskAction
from vendors.models import Vendor, VendorTask

User = get_user_model()


@pytest.fixture
def calendar_user(test_tenant):
    with tenant_context(test_tenant):
        return User.objects.create_user(
            username='calendar-owner',
            email='calendar-owner@example.com',
            password='testpass123',
        )


@pytest.fixture
def calendar_sources(test_tenant, calendar_user):
    due_date = timezone.now().date() + timedelta(days=7)
    with tenant_context(test_tenant):
        framework = Framework.objects.create(
            name='ISO 27001',
            short_name='ISO27001',
            description='Information security framework',
            issuing_organization='ISO',
            effective_date=timezone.now().date(),
            status='active',
            created_by=calendar_user,
        )
        clause = Clause.objects.create(
            framework=framework,
            clause_id='A.5.1',
            title='Policies for information security',
            description='Policy control',
        )
        control = Control.objects.create(
            name='Maintain policies',
            description='Maintain approved policies',
            control_id='CTRL-001',
            control_type='administrative',
            control_owner=calendar_user,
            created_by=calendar_user,
        )
        control.clauses.add(clause)
        ControlAssessment.objects.create(
            control=control,
            assessment_id='ASS-001',
            status='in_progress',
            assigned_to=calendar_user,
            due_date=due_date,
            created_by=calendar_user,
        )

        risk = Risk.objects.create(
            title='Supplier outage',
            description='Critical supplier outage risk',
            impact=4,
            likelihood=3,
            risk_owner=calendar_user,
            next_review_date=due_date,
            created_by=calendar_user,
        )
        RiskAction.objects.create(
            risk=risk,
            title='Confirm supplier recovery plan',
            description='Review latest recovery plan',
            assigned_to=calendar_user,
            due_date=due_date,
            created_by=calendar_user,
        )

        vendor = Vendor.objects.create(
            name='Acme Hosting',
            assigned_to=calendar_user,
            contract_end_date=due_date,
            created_by=calendar_user,
        )
        VendorTask.objects.create(
            vendor=vendor,
            task_type='security_review',
            title='Annual security review',
            due_date=due_date,
            assigned_to=calendar_user,
            created_by=calendar_user,
        )

        category = PolicyCategory.objects.create(name='Security')
        Policy.objects.create(
            title='Access Control Policy',
            category=category,
            policy_type='policy',
            owner=calendar_user,
            created_by=calendar_user,
            next_review_date=due_date,
        )

        Asset.objects.create(
            asset_id='AST-001',
            name='Customer database',
            asset_type='database',
            owner=calendar_user,
            next_review_date=due_date,
            created_by=calendar_user,
        )

        CalendarEvent.objects.create(
            title='Board risk committee',
            description='Quarterly GRC review',
            event_type='meeting',
            due_date=due_date,
            owner=calendar_user,
            created_by=calendar_user,
        )

    return due_date


@pytest.mark.django_db
def test_calendar_combined_endpoint_returns_cross_module_events(
    tenant_client,
    test_tenant,
    calendar_user,
    calendar_sources,
):
    tenant_client.defaults['HTTP_HOST'] = f'{test_tenant.schema_name}.localhost'
    tenant_client.force_authenticate(user=calendar_user)

    response = tenant_client.get('/api/calendar/events/combined/')

    assert response.status_code == 200
    source_types = {event['source_type'] for event in response.json()}
    assert {
        'control_assessment',
        'risk_review',
        'risk_action',
        'vendor_contract',
        'vendor_task',
        'policy_review',
        'asset_review',
        'custom_event',
    }.issubset(source_types)


@pytest.mark.django_db
def test_custom_event_create_records_audit_log(tenant_client, test_tenant, calendar_user):
    tenant_client.defaults['HTTP_HOST'] = f'{test_tenant.schema_name}.localhost'
    tenant_client.force_authenticate(user=calendar_user)
    due_date = timezone.now().date() + timedelta(days=10)

    response = tenant_client.post(
        '/api/calendar/events/',
        {
            'title': 'Internal audit opening meeting',
            'description': 'Kick-off annual internal audit',
            'event_type': 'meeting',
            'due_date': due_date.isoformat(),
            'owner': calendar_user.id,
        },
        format='json',
    )

    assert response.status_code == 201
    assert CalendarEvent.objects.filter(title='Internal audit opening meeting').exists()
    assert CalendarAuditLog.objects.filter(action='created').exists()


@pytest.mark.django_db
def test_notification_preferences_are_user_scoped(tenant_client, test_tenant, calendar_user):
    tenant_client.defaults['HTTP_HOST'] = f'{test_tenant.schema_name}.localhost'
    tenant_client.force_authenticate(user=calendar_user)

    response = tenant_client.post(
        '/api/calendar/preferences/',
        {'email_enabled': False, 'due_date_enabled': False},
        format='json',
    )

    assert response.status_code == 200
    preference = CalendarNotificationPreference.objects.get(user=calendar_user)
    assert preference.email_enabled is False
    assert preference.due_date_enabled is False


@pytest.mark.django_db
def test_send_due_reminders_is_idempotent(test_tenant, calendar_user, calendar_sources):
    with tenant_context(test_tenant):
        with patch('calendarhub.services.send_mail') as send_mail:
            first_result = send_due_reminders(reference_date=timezone.now().date())
            second_result = send_due_reminders(reference_date=timezone.now().date())

        assert first_result['sent'] == 8
        assert second_result['sent'] == 0
        assert CalendarReminderLog.objects.count() == 8
        assert send_mail.call_count == 8


@pytest.mark.django_db
def test_scheduled_reminder_task_iterates_tenants(test_tenant, calendar_user, calendar_sources):
    with patch('calendarhub.services.send_mail'):
        result = send_calendar_deadline_reminders()

    assert result['sent'] == 8
    assert result['tenants'][test_tenant.schema_name]['checked'] == 8
    with tenant_context(test_tenant):
        assert CalendarReminderLog.objects.count() == 8


@pytest.mark.django_db
def test_calendar_service_can_filter_owner(test_tenant, calendar_user, calendar_sources):
    with tenant_context(test_tenant):
        other_user = User.objects.create_user(
            username='other-owner',
            email='other@example.com',
            password='testpass123',
        )
        events = list_calendar_events(owner=other_user)

    assert events == []
