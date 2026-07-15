import csv
import ipaddress
import json
import subprocess
from dataclasses import dataclass
from io import StringIO
from urllib.parse import urlparse

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from risk.models import Risk, RiskAction

from .models import ScanJob, ScanTarget, VulnerabilityFinding


class TargetValidationError(ValueError):
    pass


class ScannerUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class NormalizedFinding:
    scanner_name: str
    scanner_finding_id: str
    template_id: str
    title: str
    severity: str
    description: str
    remediation: str
    matched_at: str
    cve: str
    cvss_score: float | None
    evidence: dict


def validate_scan_target_address(address):
    host = _extract_host(address)
    if not host:
        raise TargetValidationError('A hostname, IP address or URL is required.')

    allowed_suffixes = _settings_list('VULN_ALLOWED_TARGET_SUFFIXES')
    if allowed_suffixes and not any(host == suffix or host.endswith(f'.{suffix}') for suffix in allowed_suffixes):
        raise TargetValidationError('Target is outside the configured vulnerability scanning allow-list.')

    if host.lower() == 'localhost' or host.lower().endswith('.localhost') or host.lower().endswith('.local'):
        raise TargetValidationError('Localhost and local network names are not valid scan targets.')

    try:
        network = ipaddress.ip_network(host, strict=False)
    except ValueError:
        return address

    allow_private = bool(getattr(settings, 'VULN_ALLOW_PRIVATE_TARGETS', False))
    for ip in network:
        if ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved:
            raise TargetValidationError('Reserved, loopback and link-local targets are not allowed.')
        if ip.is_private and not allow_private:
            raise TargetValidationError('Private network targets require VULN_ALLOW_PRIVATE_TARGETS=true.')
        break
    return address


def create_scan_job(target, requested_by=None, schedule=None, scanner='nuclei'):
    if target.status != 'approved':
        raise ValueError('Only approved scan targets can be scanned.')
    return ScanJob.objects.create(
        target=target,
        schedule=schedule,
        scanner=scanner,
        requested_by=requested_by,
    )


def advance_schedule_after_queue(schedule, queued_at=None):
    queued_at = queued_at or timezone.now()
    if schedule.frequency == 'manual':
        schedule.is_active = False
        schedule.next_run_at = None
    elif schedule.frequency == 'daily':
        schedule.next_run_at = queued_at + timezone.timedelta(days=1)
    elif schedule.frequency == 'weekly':
        schedule.next_run_at = queued_at + timezone.timedelta(days=7)
    elif schedule.frequency == 'monthly':
        schedule.next_run_at = queued_at + relativedelta(months=1)
    schedule.save(update_fields=['is_active', 'next_run_at', 'updated_at'])


def execute_scan_job(job_id):
    with transaction.atomic():
        job = ScanJob.objects.select_for_update().select_related('target').get(id=job_id)
        if job.status not in {'queued', 'failed'}:
            return {'status': job.status, 'findings': job.findings_count}
        job.status = 'running'
        job.started_at = timezone.now()
        job.error_message = ''
        job.save(update_fields=['status', 'started_at', 'error_message', 'updated_at'])

    try:
        findings = run_target_scan(job)
    except Exception as exc:
        with transaction.atomic():
            job = ScanJob.objects.select_for_update().get(id=job_id)
            job.status = 'failed'
            job.finished_at = timezone.now()
            job.error_message = str(exc)
            job.save(update_fields=['status', 'finished_at', 'error_message', 'updated_at'])
        return {'status': 'failed', 'error': str(exc), 'findings': 0}

    with transaction.atomic():
        job = ScanJob.objects.select_for_update().select_related('target').get(id=job_id)
        stored_count = store_findings(job, findings)
        job.status = 'succeeded'
        job.finished_at = timezone.now()
        job.findings_count = stored_count
        job.raw_summary = {'normalised_findings': stored_count}
        job.save(update_fields=['status', 'finished_at', 'findings_count', 'raw_summary', 'updated_at'])
        if job.schedule:
            job.schedule.last_run_at = job.finished_at
            job.schedule.save(update_fields=['last_run_at', 'updated_at'])
    return {'status': 'succeeded', 'findings': stored_count}


def run_target_scan(job):
    if job.scanner != 'nuclei':
        raise ScannerUnavailable(f'Unsupported scanner: {job.scanner}')
    if not getattr(settings, 'VULN_SCANNER_ENABLED', False):
        raise ScannerUnavailable('Vulnerability scanner execution is disabled.')

    binary = getattr(settings, 'NUCLEI_BINARY', 'nuclei')
    timeout = int(getattr(settings, 'VULN_SCANNER_TIMEOUT_SECONDS', 900))
    command = [
        binary,
        '-jsonl',
        '-silent',
        '-target',
        job.target.address,
    ]
    # Scanner execution is worker-only, uses a validated target, and never invokes a shell.
    completed = subprocess.run(  # noqa: S603
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if completed.returncode not in {0, 1}:
        raise ScannerUnavailable(completed.stderr.strip() or 'Scanner execution failed.')
    return parse_nuclei_jsonl(completed.stdout)


def parse_nuclei_jsonl(output):
    findings = []
    for line in output.splitlines():
        if not line.strip():
            continue
        findings.append(normalise_nuclei_result(json.loads(line)))
    return findings


def normalise_nuclei_result(result):
    info = result.get('info') or {}
    classification = info.get('classification') or {}
    severity = str(info.get('severity') or 'info').lower()
    if severity not in {'critical', 'high', 'medium', 'low', 'info'}:
        severity = 'info'
    cve = classification.get('cve-id') or ''
    if isinstance(cve, list):
        cve = ','.join(cve)
    cvss_score = classification.get('cvss-score')
    return NormalizedFinding(
        scanner_name='nuclei',
        scanner_finding_id=str(result.get('template-id') or result.get('matcher-name') or ''),
        template_id=str(result.get('template-id') or ''),
        title=str(info.get('name') or result.get('template-id') or 'Vulnerability finding'),
        severity=severity,
        description=str(info.get('description') or ''),
        remediation=str(info.get('remediation') or ''),
        matched_at=str(result.get('matched-at') or result.get('host') or ''),
        cve=str(cve),
        cvss_score=float(cvss_score) if cvss_score not in {None, ''} else None,
        evidence=result,
    )


def store_findings(job, findings):
    stored_count = 0
    for finding in findings:
        fingerprint = VulnerabilityFinding.make_fingerprint(
            finding.scanner_name,
            finding.scanner_finding_id,
            finding.matched_at,
            finding.title,
        )
        VulnerabilityFinding.objects.update_or_create(
            target=job.target,
            fingerprint=fingerprint,
            defaults={
                'job': job,
                'scanner_name': finding.scanner_name,
                'scanner_finding_id': finding.scanner_finding_id,
                'template_id': finding.template_id,
                'title': finding.title,
                'severity': finding.severity,
                'description': finding.description,
                'remediation': finding.remediation,
                'matched_at': finding.matched_at,
                'cve': finding.cve,
                'cvss_score': finding.cvss_score,
                'evidence': finding.evidence,
                'status': 'open',
                'last_seen_at': timezone.now(),
            },
        )
        stored_count += 1
    return stored_count


def create_risk_from_finding(finding, user=None):
    impact, likelihood = _severity_to_risk_rating(finding.severity)
    risk = Risk.objects.create(
        title=f'Vulnerability: {finding.title}',
        description=_finding_description(finding),
        impact=impact,
        likelihood=likelihood,
        treatment_strategy='mitigate',
        status='identified',
        risk_owner=user,
        created_by=user,
        next_review_date=timezone.now().date() + timezone.timedelta(days=30),
    )
    finding.risk = risk
    finding.save(update_fields=['risk', 'updated_at'])
    return risk


def create_risk_action_from_finding(finding, user=None):
    risk = finding.risk or create_risk_from_finding(finding, user=user)
    action = RiskAction.objects.create(
        risk=risk,
        title=f'Remediate vulnerability: {finding.title}',
        description=finding.remediation or 'Remediate or document an accepted risk decision for this finding.',
        action_type='technical',
        assigned_to=user,
        priority=_severity_to_priority(finding.severity),
        due_date=timezone.now().date() + timezone.timedelta(days=_severity_to_due_days(finding.severity)),
        created_by=user,
    )
    finding.risk_action = action
    finding.save(update_fields=['risk_action', 'updated_at'])
    return action


def export_findings_csv(queryset):
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['target', 'title', 'severity', 'status', 'cve', 'matched_at', 'first_seen_at', 'last_seen_at'])
    for finding in queryset.select_related('target'):
        writer.writerow([
            finding.target.name,
            finding.title,
            finding.severity,
            finding.status,
            finding.cve,
            finding.matched_at,
            finding.first_seen_at.isoformat(),
            finding.last_seen_at.isoformat(),
        ])
    return buffer.getvalue()


def _extract_host(address):
    parsed = urlparse(address if '://' in address else f'//{address}')
    if parsed.username or parsed.password:
        raise TargetValidationError('Scan target URLs must not include credentials.')
    return parsed.hostname or address


def _settings_list(name):
    value = getattr(settings, name, [])
    if isinstance(value, str):
        return [item.strip().lstrip('.') for item in value.split(',') if item.strip()]
    return [str(item).strip().lstrip('.') for item in value if str(item).strip()]


def _severity_to_risk_rating(severity):
    return {
        'critical': (5, 4),
        'high': (4, 4),
        'medium': (3, 3),
        'low': (2, 2),
        'info': (1, 1),
    }.get(severity, (2, 2))


def _severity_to_priority(severity):
    return {
        'critical': 'critical',
        'high': 'high',
        'medium': 'medium',
        'low': 'low',
        'info': 'low',
    }.get(severity, 'medium')


def _severity_to_due_days(severity):
    return {
        'critical': 7,
        'high': 14,
        'medium': 30,
        'low': 60,
        'info': 90,
    }.get(severity, 30)


def _finding_description(finding):
    parts = [
        finding.description,
        f'Target: {finding.target.address}',
        f'Matched at: {finding.matched_at}',
        f'CVE: {finding.cve}' if finding.cve else '',
    ]
    return '\n\n'.join(part for part in parts if part)
