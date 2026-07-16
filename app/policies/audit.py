from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.db.models import Model

from core.audit import build_audit_details

from .models import PolicyVersionAuditLog


POLICY_VERSION_FIELDS = (
    'policy_id',
    'version_number',
    'lifecycle_state',
    'is_active',
    'is_published',
    'approved_at',
    'approved_by_id',
    'finalized_at',
    'finalized_by_id',
    'effective_date',
    'expiry_date',
    'document_size',
    'final_pdf_size',
)


def snapshot_policy_version(version) -> dict[str, Any]:
    payload = {field: _serialise(getattr(version, field, None)) for field in POLICY_VERSION_FIELDS}
    payload.update(
        {
            'policy_code': version.policy.policy_code,
            'policy_title': version.policy.title,
            'source_filename': version.file_name or '',
            'final_pdf_filename': _file_basename(version.final_pdf.name),
        }
    )
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


def log_policy_version_event(
    *,
    version,
    action: str,
    actor,
    request=None,
    previous: Mapping[str, Any] | None = None,
    new: Mapping[str, Any] | None = None,
    reason: str = '',
    source: Mapping[str, Any] | None = None,
    details: Mapping[str, Any] | None = None,
):
    event_name = f"POLICY_VERSION_{action.upper()}"
    payload = build_audit_details(
        event=event_name,
        actor=actor,
        target=version,
        object_display=policy_version_display(version),
        previous=previous,
        new=new,
        reason=reason,
        request=request,
        source=source or {'type': 'api', 'reference': ''},
        details=details,
    )
    return PolicyVersionAuditLog.objects.create(
        policy_version=version,
        action=action,
        actor=actor if getattr(actor, 'is_authenticated', False) else None,
        details=payload,
    )


def policy_version_display(version) -> str:
    return f'{version.policy.policy_code} v{version.version_number}'


def _serialise(value):
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Model):
        return str(value.pk)
    return value


def _file_basename(name):
    if not name:
        return ''
    return name.rsplit('/', 1)[-1]
