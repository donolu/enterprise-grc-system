from __future__ import annotations

from collections.abc import Mapping

from core.audit import changed_values, log_audit_event, serialise_audit_value, snapshot_model


RISK_FIELDS = (
    'risk_id',
    'title',
    'category_id',
    'impact',
    'likelihood',
    'risk_level',
    'status',
    'treatment_strategy',
    'treatment_description',
    'risk_owner_id',
    'risk_matrix_id',
    'identified_date',
    'last_assessed_date',
    'next_review_date',
    'closed_date',
)
RISK_ACTION_FIELDS = (
    'action_id',
    'risk_id',
    'title',
    'action_type',
    'assigned_to_id',
    'status',
    'priority',
    'start_date',
    'due_date',
    'completed_date',
    'progress_percentage',
    'estimated_cost',
    'actual_cost',
    'estimated_effort_hours',
)
RISK_ACTION_EVIDENCE_FIELDS = (
    'action_id',
    'title',
    'evidence_type',
    'external_link',
    'is_validated',
    'validated_by_id',
    'validated_at',
    'evidence_date',
    'uploaded_by_id',
)


def snapshot_risk(risk):
    return snapshot_model(risk, RISK_FIELDS)


def snapshot_risk_action(action):
    return snapshot_model(action, RISK_ACTION_FIELDS)


def snapshot_risk_action_evidence(evidence):
    payload = snapshot_model(evidence, RISK_ACTION_EVIDENCE_FIELDS)
    payload['file'] = {
        'present': bool(evidence.file),
        'name': evidence.file.name if evidence.file else '',
    }
    return payload


def audit_risk_change(
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


def risk_changed_values(previous, new):
    return changed_values(previous, new)


def risk_display(risk) -> str:
    return risk.risk_id or f'risk:{risk.pk}'


def risk_action_display(action) -> str:
    return action.action_id or f'risk-action:{action.pk}'


def risk_action_evidence_display(evidence) -> str:
    return f'{evidence.action.action_id}:{evidence.pk}'


def serialise(value):
    return serialise_audit_value(value)
