from __future__ import annotations

from collections.abc import Mapping

from core.audit import changed_values, log_audit_event, snapshot_model


VENDOR_FIELDS = (
    'vendor_id',
    'name',
    'legal_name',
    'category_id',
    'status',
    'vendor_type',
    'risk_level',
    'risk_score',
    'annual_spend',
    'compliance_status',
    'data_processing_agreement',
    'security_assessment_completed',
    'security_assessment_date',
    'assigned_to_id',
    'relationship_start_date',
    'primary_contract_number',
    'contract_start_date',
    'contract_end_date',
    'auto_renewal',
    'renewal_notice_days',
    'performance_score',
    'last_performance_review',
    'tags',
)
VENDOR_TASK_FIELDS = (
    'task_id',
    'vendor_id',
    'task_type',
    'title',
    'due_date',
    'start_date',
    'completed_date',
    'priority',
    'status',
    'assigned_to_id',
    'reminder_days',
    'related_contract_number',
    'service_reference_id',
    'attachments',
    'is_recurring',
    'recurrence_pattern',
    'auto_generated',
    'generation_source',
)


def snapshot_vendor(vendor):
    return snapshot_model(vendor, VENDOR_FIELDS)


def snapshot_vendor_task(task):
    return snapshot_model(task, VENDOR_TASK_FIELDS)


def audit_vendor_change(
    *,
    event: str,
    actor,
    target,
    object_display: str,
    request=None,
    previous: Mapping | None = None,
    new: Mapping | None = None,
    reason: str = '',
    source: Mapping | None = None,
    details: Mapping | None = None,
):
    return log_audit_event(
        event=event,
        actor=actor,
        target=target,
        object_display=object_display,
        previous=previous,
        new=new,
        reason=reason,
        request=request,
        source=source or {'type': 'api', 'reference': ''},
        details=details,
    )


def vendor_changed_values(previous, new):
    return changed_values(previous, new)


def vendor_display(vendor) -> str:
    return vendor.vendor_id or f'vendor:{vendor.pk}'


def vendor_task_display(task) -> str:
    return task.task_id or f'vendor-task:{task.pk}'
