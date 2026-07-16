from __future__ import annotations

from collections.abc import Mapping

from core.audit import changed_values, log_audit_event, serialise_audit_value, snapshot_model


ASSET_FIELDS = (
    'asset_id',
    'name',
    'asset_type',
    'classification',
    'criticality',
    'lifecycle_status',
    'owner_id',
    'owner_name',
    'custodian',
    'location',
    'domain',
    'ip_address',
    'serial_number',
    'manufacturer',
    'model',
    'operating_system',
    'version',
    'last_seen_at',
    'last_reviewed_at',
    'next_review_date',
    'disposal_date',
)


def snapshot_asset(asset):
    payload = snapshot_model(asset, ASSET_FIELDS)
    if asset.pk:
        payload['linked_risk_ids'] = [
            str(pk) for pk in asset.linked_risks.order_by('pk').values_list('pk', flat=True)
        ]
        payload['linked_control_ids'] = [
            str(pk) for pk in asset.linked_controls.order_by('pk').values_list('pk', flat=True)
        ]
        payload['linked_document_ids'] = [
            str(pk) for pk in asset.linked_documents.order_by('pk').values_list('pk', flat=True)
        ]
    return payload


def audit_asset_change(
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


def asset_changed_values(previous, new):
    return changed_values(previous, new)


def asset_display(asset) -> str:
    return asset.asset_id or f'asset:{asset.pk}'


def serialise(value):
    return serialise_audit_value(value)
