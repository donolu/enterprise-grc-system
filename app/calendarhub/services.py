from dataclasses import dataclass
from datetime import date

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from assets.models import Asset
from catalogs.models import ControlAssessment
from policies.models import Policy
from risk.models import Risk, RiskAction
from vendors.models import Vendor, VendorTask

from .models import (
    CalendarAuditLog,
    CalendarEvent,
    CalendarNotificationPreference,
    CalendarReminderLog,
)

User = get_user_model()


@dataclass(frozen=True)
class CalendarSourceEvent:
    source_type: str
    source_id: str
    title: str
    due_date: date
    owner: User | None
    source_url: str
    status: str
    module: str
    metadata: dict

    @property
    def days_until_due(self):
        return (self.due_date - timezone.now().date()).days

    @property
    def is_overdue(self):
        return self.days_until_due < 0 and self.status not in {'complete', 'completed', 'cancelled', 'closed'}

    def to_dict(self):
        owner = None
        if self.owner:
            owner = {
                'id': self.owner.id,
                'email': self.owner.email,
                'name': self.owner.get_full_name() or self.owner.username,
            }
        return {
            'source_type': self.source_type,
            'source_id': self.source_id,
            'title': self.title,
            'due_date': self.due_date,
            'owner': owner,
            'source_url': self.source_url,
            'status': self.status,
            'module': self.module,
            'metadata': self.metadata,
            'days_until_due': self.days_until_due,
            'is_overdue': self.is_overdue,
        }


def list_calendar_events(start_date=None, end_date=None, owner=None):
    events = [
        *list_custom_events(start_date=start_date, end_date=end_date, owner=owner),
        *list_assessment_events(start_date=start_date, end_date=end_date, owner=owner),
        *list_risk_events(start_date=start_date, end_date=end_date, owner=owner),
        *list_vendor_events(start_date=start_date, end_date=end_date, owner=owner),
        *list_policy_events(start_date=start_date, end_date=end_date, owner=owner),
        *list_asset_events(start_date=start_date, end_date=end_date, owner=owner),
    ]
    return sorted(events, key=lambda event: (event.due_date, event.module, event.title))


def list_custom_events(start_date=None, end_date=None, owner=None):
    queryset = CalendarEvent.objects.exclude(status='cancelled').select_related('owner')
    queryset = _date_filter(queryset, 'due_date', start_date, end_date)
    if owner:
        queryset = queryset.filter(owner=owner)
    return [
        CalendarSourceEvent(
            source_type='custom_event',
            source_id=str(event.id),
            title=event.title,
            due_date=event.due_date,
            owner=event.owner,
            source_url=event.source_url or f'/api/calendar/events/{event.id}/',
            status=event.status,
            module='calendar',
            metadata={'event_type': event.event_type, **event.metadata},
        )
        for event in queryset
    ]


def list_assessment_events(start_date=None, end_date=None, owner=None):
    queryset = ControlAssessment.objects.filter(due_date__isnull=False).exclude(
        status__in=['complete', 'not_applicable']
    ).select_related('assigned_to', 'control')
    queryset = _date_filter(queryset, 'due_date', start_date, end_date)
    if owner:
        queryset = queryset.filter(assigned_to=owner)
    return [
        CalendarSourceEvent(
            source_type='control_assessment',
            source_id=str(assessment.id),
            title=f'Control assessment due: {assessment.control.control_id}',
            due_date=assessment.due_date,
            owner=assessment.assigned_to,
            source_url=f'/api/catalogs/assessments/{assessment.id}/',
            status=assessment.status,
            module='frameworks',
            metadata={
                'assessment_id': assessment.assessment_id,
                'control_id': assessment.control.control_id,
                'remediation_due_date': (
                    assessment.remediation_due_date.isoformat()
                    if assessment.remediation_due_date
                    else None
                ),
            },
        )
        for assessment in queryset
    ]


def list_risk_events(start_date=None, end_date=None, owner=None):
    review_queryset = Risk.objects.filter(next_review_date__isnull=False).exclude(
        status__in=['closed', 'transferred']
    ).select_related('risk_owner')
    review_queryset = _date_filter(review_queryset, 'next_review_date', start_date, end_date)
    action_queryset = RiskAction.objects.exclude(status__in=['completed', 'cancelled']).select_related(
        'assigned_to', 'risk'
    )
    action_queryset = _date_filter(action_queryset, 'due_date', start_date, end_date)
    if owner:
        review_queryset = review_queryset.filter(risk_owner=owner)
        action_queryset = action_queryset.filter(assigned_to=owner)

    return [
        *[
            CalendarSourceEvent(
                source_type='risk_review',
                source_id=str(risk.id),
                title=f'Risk review due: {risk.title}',
                due_date=risk.next_review_date,
                owner=risk.risk_owner,
                source_url=f'/api/risk/risks/{risk.id}/',
                status=risk.status,
                module='risk',
                metadata={'risk_id': risk.risk_id, 'risk_level': risk.risk_level},
            )
            for risk in review_queryset
        ],
        *[
            CalendarSourceEvent(
                source_type='risk_action',
                source_id=str(action.id),
                title=f'Risk action due: {action.title}',
                due_date=action.due_date,
                owner=action.assigned_to,
                source_url=f'/api/risk/actions/{action.id}/',
                status=action.status,
                module='risk',
                metadata={'action_id': action.action_id, 'risk_id': action.risk.risk_id},
            )
            for action in action_queryset
        ],
    ]


def list_vendor_events(start_date=None, end_date=None, owner=None):
    vendor_queryset = Vendor.objects.filter(contract_end_date__isnull=False).exclude(
        status__in=['terminated', 'inactive']
    ).select_related('assigned_to')
    vendor_queryset = _date_filter(vendor_queryset, 'contract_end_date', start_date, end_date)
    task_queryset = VendorTask.objects.exclude(status__in=['completed', 'cancelled']).select_related(
        'assigned_to', 'vendor'
    )
    task_queryset = _date_filter(task_queryset, 'due_date', start_date, end_date)
    if owner:
        vendor_queryset = vendor_queryset.filter(assigned_to=owner)
        task_queryset = task_queryset.filter(assigned_to=owner)

    return [
        *[
            CalendarSourceEvent(
                source_type='vendor_contract',
                source_id=str(vendor.id),
                title=f'Vendor contract expires: {vendor.name}',
                due_date=vendor.contract_end_date,
                owner=vendor.assigned_to,
                source_url=f'/api/vendors/vendors/{vendor.id}/',
                status=vendor.status,
                module='vendors',
                metadata={'vendor_id': vendor.vendor_id},
            )
            for vendor in vendor_queryset
        ],
        *[
            CalendarSourceEvent(
                source_type='vendor_task',
                source_id=str(task.id),
                title=f'Vendor task due: {task.title}',
                due_date=task.due_date,
                owner=task.assigned_to,
                source_url=f'/api/vendors/tasks/{task.id}/',
                status=task.status,
                module='vendors',
                metadata={'task_id': task.task_id, 'vendor_id': task.vendor.vendor_id},
            )
            for task in task_queryset
        ],
    ]


def list_policy_events(start_date=None, end_date=None, owner=None):
    queryset = Policy.objects.filter(next_review_date__isnull=False).exclude(status='archived').select_related('owner')
    queryset = _date_filter(queryset, 'next_review_date', start_date, end_date)
    if owner:
        queryset = queryset.filter(owner=owner)
    return [
        CalendarSourceEvent(
            source_type='policy_review',
            source_id=str(policy.id),
            title=f'Policy review due: {policy.title}',
            due_date=policy.next_review_date,
            owner=policy.owner,
            source_url=f'/api/policies/policies/{policy.id}/',
            status=policy.status,
            module='policies',
            metadata={'policy_code': policy.policy_code, 'policy_type': policy.policy_type},
        )
        for policy in queryset
    ]


def list_asset_events(start_date=None, end_date=None, owner=None):
    queryset = Asset.objects.filter(next_review_date__isnull=False).exclude(
        lifecycle_status__in=['retired', 'disposed']
    ).select_related('owner')
    queryset = _date_filter(queryset, 'next_review_date', start_date, end_date)
    if owner:
        queryset = queryset.filter(owner=owner)
    return [
        CalendarSourceEvent(
            source_type='asset_review',
            source_id=str(asset.id),
            title=f'Asset review due: {asset.name}',
            due_date=asset.next_review_date,
            owner=asset.owner,
            source_url=f'/api/assets/assets/{asset.id}/',
            status=asset.lifecycle_status,
            module='assets',
            metadata={'asset_id': asset.asset_id, 'criticality': asset.criticality},
        )
        for asset in queryset
    ]


def send_due_reminders(reference_date=None):
    reference_date = reference_date or timezone.now().date()
    window_end = reference_date + timezone.timedelta(days=7)
    events = list_calendar_events(end_date=window_end)
    sent = 0
    skipped = 0

    for event in events:
        reminder_type = _reminder_type_for_event(event, reference_date)
        if not reminder_type or not event.owner or not event.owner.email:
            skipped += 1
            continue
        if not _preference_allows(event.owner, reminder_type):
            skipped += 1
            continue
        created = create_reminder_log(event, event.owner, reminder_type)
        if not created:
            skipped += 1
            continue
        _send_reminder_email(event, event.owner, reminder_type)
        sent += 1

    return {'sent': sent, 'skipped': skipped, 'checked': len(events)}


def create_reminder_log(event, recipient, reminder_type):
    try:
        with transaction.atomic():
            log, created = CalendarReminderLog.objects.get_or_create(
                source_type=event.source_type,
                source_id=event.source_id,
                recipient=recipient,
                due_date=event.due_date,
                reminder_type=reminder_type,
                defaults={
                    'title': event.title,
                    'email_sent': True,
                    'metadata': event.metadata,
                },
            )
            if created:
                CalendarAuditLog.objects.create(
                    action='reminder_sent',
                    source_type=event.source_type,
                    source_id=event.source_id,
                    actor=recipient,
                    details={'reminder_log_id': log.id, 'reminder_type': reminder_type},
                )
            return created
    except IntegrityError:
        return False


def _date_filter(queryset, field_name, start_date, end_date):
    if start_date:
        queryset = queryset.filter(**{f'{field_name}__gte': start_date})
    if end_date:
        queryset = queryset.filter(**{f'{field_name}__lte': end_date})
    return queryset


def _reminder_type_for_event(event, reference_date):
    days_until_due = (event.due_date - reference_date).days
    if days_until_due == 7:
        return 'advance_warning'
    if days_until_due == 0:
        return 'due_today'
    if days_until_due < 0:
        return 'overdue'
    return None


def _preference_allows(user, reminder_type):
    preference, _ = CalendarNotificationPreference.objects.get_or_create(user=user)
    if not preference.email_enabled:
        return False
    if reminder_type == 'advance_warning':
        return preference.advance_reminder_days == 7
    if reminder_type == 'due_today':
        return preference.due_date_enabled
    if reminder_type == 'overdue':
        return preference.overdue_enabled
    return False


def _send_reminder_email(event, recipient, reminder_type):
    subject = f'GRC deadline reminder: {event.title}'
    body = (
        f'{event.title}\n\n'
        f'Due date: {event.due_date.isoformat()}\n'
        f'Module: {event.module}\n'
        f'Reminder type: {reminder_type.replace("_", " ")}\n'
        f'Open item: {event.source_url}\n'
    )
    send_mail(subject, body, None, [recipient.email], fail_silently=True)
