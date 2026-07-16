from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.db.models import Model

from core.audit import log_audit_event


FRAMEWORK_FIELDS = (
    'name',
    'short_name',
    'version',
    'framework_type',
    'status',
    'effective_date',
    'expiry_date',
    'is_mandatory',
)
CLAUSE_FIELDS = (
    'framework_id',
    'clause_id',
    'title',
    'clause_type',
    'criticality',
    'is_testable',
    'parent_clause_id',
    'sort_order',
)
CONTROL_FIELDS = (
    'control_id',
    'name',
    'control_type',
    'automation_level',
    'status',
    'control_owner_id',
    'business_owner',
    'effectiveness_rating',
    'risk_rating',
    'version',
)
ASSESSMENT_FIELDS = (
    'framework_id',
    'control_id',
    'applicability',
    'status',
    'implementation_status',
    'assigned_to_id',
    'reviewer_id',
    'due_date',
    'risk_rating',
    'compliance_score',
    'remediation_owner_id',
)
ASSESSMENT_EVIDENCE_FIELDS = (
    'assessment_id',
    'evidence_id',
    'evidence_purpose',
    'is_primary_evidence',
)


def snapshot_model(instance: Model, fields: Iterable[str]) -> dict[str, Any]:
    return {field: _serialise(getattr(instance, field, None)) for field in fields}


def snapshot_control(instance) -> dict[str, Any]:
    payload = snapshot_model(instance, CONTROL_FIELDS)
    if instance.pk:
        payload['clause_ids'] = [
            str(pk) for pk in instance.clauses.order_by('pk').values_list('pk', flat=True)
        ]
        payload['framework_ids'] = [
            str(pk)
            for pk in instance.clauses.order_by('framework_id')
            .values_list('framework_id', flat=True)
            .distinct()
        ]
    return payload


def changed_values(previous: Mapping[str, Any], new: Mapping[str, Any]):
    previous_changed = {}
    new_changed = {}
    for key, previous_value in previous.items():
        new_value = new.get(key)
        if previous_value != new_value:
            previous_changed[key] = previous_value
            new_changed[key] = new_value
    for key, new_value in new.items():
        if key not in previous:
            previous_changed[key] = None
            new_changed[key] = new_value
    return previous_changed, new_changed


def audit_catalogue_change(
    *,
    event: str,
    actor,
    target,
    object_display: str,
    request=None,
    previous: Mapping[str, Any] | None = None,
    new: Mapping[str, Any] | None = None,
    reason: str = '',
    source: Mapping[str, Any] | None = None,
    details: Mapping[str, Any] | None = None,
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


def framework_display(framework) -> str:
    return f'{framework.short_name or framework.name} v{framework.version}'


def clause_display(clause) -> str:
    return f'{clause.framework.short_name} {clause.clause_id}'


def control_display(control) -> str:
    return control.control_id


def assessment_display(assessment) -> str:
    return assessment.assessment_id


def assessment_evidence_display(link) -> str:
    return f'{link.assessment.assessment_id}:{link.evidence_id}'


def _serialise(value):
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Model):
        return str(value.pk)
    if isinstance(value, list):
        return [_serialise(item) for item in value]
    if isinstance(value, tuple):
        return [_serialise(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialise(item) for key, item in value.items()}
    return value
