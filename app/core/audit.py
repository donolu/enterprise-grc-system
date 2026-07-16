from __future__ import annotations

from collections.abc import Mapping
from typing import Any


SYSTEM_ACTOR = {'id': None, 'email': 'system', 'type': 'system'}


def log_audit_event(
    *,
    event: str,
    actor=None,
    target=None,
    object_type: str | None = None,
    object_id: str | int | None = None,
    object_display: str = '',
    previous: Mapping[str, Any] | None = None,
    new: Mapping[str, Any] | None = None,
    reason: str = '',
    request=None,
    source: Mapping[str, Any] | None = None,
    details: Mapping[str, Any] | None = None,
):
    """
    Write a tenant-scoped audit event using the platform standard payload.

    The caller controls object_display so sensitive tenant content is not
    accidentally copied into the audit trail through a model __str__ method.
    """
    from core.models import AuditEvent

    payload = build_audit_details(
        event=event,
        actor=actor,
        target=target,
        object_type=object_type,
        object_id=object_id,
        object_display=object_display,
        previous=previous,
        new=new,
        reason=reason,
        request=request,
        source=source,
        details=details,
    )
    return AuditEvent.objects.create(
        user=actor if _is_user(actor) else None,
        event=event,
        details=payload,
    )


def build_audit_details(
    *,
    event: str,
    actor=None,
    target=None,
    object_type: str | None = None,
    object_id: str | int | None = None,
    object_display: str = '',
    previous: Mapping[str, Any] | None = None,
    new: Mapping[str, Any] | None = None,
    reason: str = '',
    request=None,
    source: Mapping[str, Any] | None = None,
    details: Mapping[str, Any] | None = None,
):
    object_payload = _object_payload(
        target=target,
        object_type=object_type,
        object_id=object_id,
        object_display=object_display,
    )
    payload = {
        'actor': _actor_payload(actor),
        'object': object_payload,
        'event': event,
        'previous': _clean_mapping(previous),
        'new': _clean_mapping(new),
        'reason': reason or '',
        'request': _request_payload(request),
        'source': _source_payload(source),
    }
    if details:
        payload.update(dict(details))
    return payload


def _actor_payload(actor):
    if actor is None:
        return SYSTEM_ACTOR.copy()
    if isinstance(actor, Mapping):
        return {
            'id': _string_or_none(actor.get('id')),
            'email': str(actor.get('email') or ''),
            'type': str(actor.get('type') or 'system'),
        }
    if not getattr(actor, 'is_authenticated', False):
        return SYSTEM_ACTOR.copy()
    return {
        'id': _string_or_none(getattr(actor, 'pk', None)),
        'email': getattr(actor, 'email', '') or getattr(actor, 'username', '') or '',
        'type': 'user',
    }


def _object_payload(*, target, object_type, object_id, object_display):
    if target is not None:
        object_type = object_type or target._meta.label
        object_id = object_id if object_id is not None else target.pk
    return {
        'type': object_type or '',
        'id': _string_or_none(object_id),
        'display': object_display or '',
    }


def _request_payload(request):
    if request is None:
        return {'ip': '', 'user_agent': '', 'request_id': ''}

    meta = getattr(request, 'META', {})
    forwarded_for = meta.get('HTTP_X_FORWARDED_FOR', '')
    ip_address = forwarded_for.split(',')[0].strip() if forwarded_for else meta.get('REMOTE_ADDR', '')
    return {
        'ip': ip_address or '',
        'user_agent': meta.get('HTTP_USER_AGENT', ''),
        'request_id': meta.get('HTTP_X_REQUEST_ID', ''),
    }


def _source_payload(source):
    if not source:
        return {'type': '', 'reference': ''}
    return {
        'type': str(source.get('type') or ''),
        'reference': str(source.get('reference') or ''),
    }


def _clean_mapping(value):
    if not value:
        return {}
    return dict(value)


def _string_or_none(value):
    if value is None:
        return None
    return str(value)


def _is_user(value):
    return bool(
        value is not None
        and hasattr(value, 'pk')
        and getattr(value, 'is_authenticated', False)
    )
