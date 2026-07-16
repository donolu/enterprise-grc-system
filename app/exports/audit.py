from __future__ import annotations

from collections.abc import Mapping

from core.audit import changed_values, log_audit_event, snapshot_model


ASSESSMENT_REPORT_FIELDS = (
    'report_type',
    'title',
    'framework_id',
    'requested_by_id',
    'status',
    'generated_file_id',
    'generation_started_at',
    'generation_completed_at',
    'include_evidence_summary',
    'include_implementation_notes',
    'include_overdue_items',
    'include_charts',
)
TENANT_DATA_EXPORT_FIELDS = (
    'title',
    'export_format',
    'selected_modules',
    'requested_by_id',
    'status',
    'generated_file_id',
    'generation_started_at',
    'generation_completed_at',
    'record_counts',
    'coverage_manifest',
)


def snapshot_assessment_report(report):
    payload = snapshot_model(report, ASSESSMENT_REPORT_FIELDS)
    payload['assessment_ids'] = [
        str(pk) for pk in report.assessments.order_by('pk').values_list('pk', flat=True)
    ] if report.pk else []
    return payload


def snapshot_tenant_data_export(data_export):
    return snapshot_model(data_export, TENANT_DATA_EXPORT_FIELDS)


def audit_export_change(
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


def export_changed_values(previous, new):
    return changed_values(previous, new)


def assessment_report_display(report) -> str:
    return f'assessment-report:{report.pk}'


def tenant_data_export_display(data_export) -> str:
    return f'tenant-data-export:{data_export.pk}'
