from __future__ import annotations

from collections.abc import Mapping

from core.audit import changed_values, log_audit_event, snapshot_model


DOCUMENT_FIELDS = (
    'title',
    'description',
    'uploaded_by_id',
    'file_size',
    'mime_type',
    'is_public',
)


def snapshot_document(document):
    payload = snapshot_model(document, DOCUMENT_FIELDS)
    payload['file'] = {
        'present': bool(document.file),
        'name': document.file.name if document.file else '',
    }
    return payload


def audit_document_change(
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


def document_changed_values(previous, new):
    return changed_values(previous, new)


def document_display(document) -> str:
    return f'document:{document.pk}'
