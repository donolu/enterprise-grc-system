from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from django_tenants.utils import tenant_context

from risk.models import Risk, RiskAction
from vuln.models import ScanJob, ScanSchedule, ScanTarget, VulnerabilityFinding
from vuln.services import NormalizedFinding, execute_scan_job, parse_nuclei_jsonl
from vuln.tasks import run_due_scan_schedules, run_scan_job

User = get_user_model()


@pytest.fixture
def vuln_user(test_tenant):
    with tenant_context(test_tenant):
        return User.objects.create_user(
            username='scanner-owner',
            email='scanner-owner@example.com',
            password='testpass123',
        )


@pytest.fixture
def approved_target(test_tenant, vuln_user):
    with tenant_context(test_tenant):
        return ScanTarget.objects.create(
            name='Public web app',
            target_type='web',
            address='https://app.example.com',
            status='approved',
            owner=vuln_user,
            created_by=vuln_user,
        )


@pytest.mark.django_db
def test_scan_target_rejects_localhost(tenant_client, test_tenant, vuln_user):
    tenant_client.defaults['HTTP_HOST'] = f'{test_tenant.schema_name}.localhost'
    tenant_client.force_authenticate(user=vuln_user)

    response = tenant_client.post(
        '/api/vuln/targets/',
        {
            'name': 'Local target',
            'target_type': 'web',
            'address': 'http://localhost:8000',
            'status': 'approved',
        },
        format='json',
    )

    assert response.status_code == 400
    assert 'address' in response.json()


@pytest.mark.django_db
def test_start_scan_requires_approved_target_and_queues_task(tenant_client, test_tenant, vuln_user):
    tenant_client.defaults['HTTP_HOST'] = f'{test_tenant.schema_name}.localhost'
    tenant_client.force_authenticate(user=vuln_user)
    with tenant_context(test_tenant):
        target = ScanTarget.objects.create(
            name='Pending target',
            target_type='web',
            address='https://pending.example.com',
            owner=vuln_user,
            created_by=vuln_user,
        )

    blocked = tenant_client.post(f'/api/vuln/targets/{target.id}/start-scan/')
    assert blocked.status_code == 400

    with tenant_context(test_tenant):
        target.status = 'approved'
        target.save(update_fields=['status'])

    with patch('vuln.views.run_scan_job.delay') as delay:
        response = tenant_client.post(f'/api/vuln/targets/{target.id}/start-scan/')

    assert response.status_code == 202
    assert ScanJob.objects.filter(target=target, status='queued').exists()
    delay.assert_called_once()


@pytest.mark.django_db
def test_execute_scan_job_stores_normalised_findings(test_tenant, approved_target):
    finding = NormalizedFinding(
        scanner_name='nuclei',
        scanner_finding_id='CVE-2026-0001',
        template_id='cves/2026/CVE-2026-0001',
        title='Example high severity issue',
        severity='high',
        description='A high severity issue was found.',
        remediation='Apply the vendor patch.',
        matched_at='https://app.example.com/login',
        cve='CVE-2026-0001',
        cvss_score=8.1,
        evidence={'template-id': 'cves/2026/CVE-2026-0001'},
    )
    with tenant_context(test_tenant):
        job = ScanJob.objects.create(target=approved_target)
        with patch('vuln.services.run_target_scan', return_value=[finding]):
            result = execute_scan_job(job.id)
            second_result = execute_scan_job(job.id)

        assert result == {'status': 'succeeded', 'findings': 1}
        assert second_result == {'status': 'succeeded', 'findings': 1}
        stored = VulnerabilityFinding.objects.get(target=approved_target)
        assert stored.severity == 'high'
        assert stored.cve == 'CVE-2026-0001'


@pytest.mark.django_db
def test_tenant_aware_scan_task_executes_inside_target_schema(test_tenant, approved_target):
    with tenant_context(test_tenant):
        job = ScanJob.objects.create(target=approved_target)

    with patch(
        'vuln.services.run_target_scan',
        return_value=[
            NormalizedFinding(
                scanner_name='nuclei',
                scanner_finding_id='finding-1',
                template_id='template-1',
                title='Finding from task',
                severity='medium',
                description='Task finding',
                remediation='Fix it',
                matched_at='https://app.example.com',
                cve='',
                cvss_score=None,
                evidence={},
            )
        ],
    ):
        result = run_scan_job(str(job.id), test_tenant.schema_name)

    assert result == {'status': 'succeeded', 'findings': 1}
    with tenant_context(test_tenant):
        assert VulnerabilityFinding.objects.filter(title='Finding from task').exists()


@pytest.mark.django_db
def test_due_schedule_dispatcher_advances_next_run(test_tenant, approved_target):
    due_at = timezone.now() - timezone.timedelta(minutes=5)
    with tenant_context(test_tenant):
        schedule = ScanSchedule.objects.create(
            target=approved_target,
            name='Daily web scan',
            frequency='daily',
            next_run_at=due_at,
        )

    with patch('vuln.tasks.run_scan_job.delay') as delay:
        result = run_due_scan_schedules()

    assert result['queued'] == 1
    delay.assert_called_once()
    with tenant_context(test_tenant):
        schedule.refresh_from_db()
        assert schedule.next_run_at > timezone.now()
        assert ScanJob.objects.filter(schedule=schedule, status='queued').exists()


@pytest.mark.django_db
def test_finding_can_create_risk_and_remediation_action(tenant_client, test_tenant, vuln_user, approved_target):
    tenant_client.defaults['HTTP_HOST'] = f'{test_tenant.schema_name}.localhost'
    tenant_client.force_authenticate(user=vuln_user)
    with tenant_context(test_tenant):
        job = ScanJob.objects.create(target=approved_target, status='succeeded')
        finding = VulnerabilityFinding.objects.create(
            target=approved_target,
            job=job,
            fingerprint='abc123',
            title='Critical exposed admin panel',
            severity='critical',
            matched_at='https://app.example.com/admin',
        )

    risk_response = tenant_client.post(f'/api/vuln/findings/{finding.id}/create-risk/')
    action_response = tenant_client.post(f'/api/vuln/findings/{finding.id}/create-risk-action/')

    assert risk_response.status_code == 201
    assert action_response.status_code == 201
    assert Risk.objects.count() == 1
    assert RiskAction.objects.count() == 1


@override_settings(VULN_SCANNER_ENABLED=True)
def test_parse_nuclei_jsonl_normalises_result():
    findings = parse_nuclei_jsonl(
        '{"template-id":"cves/2026/CVE-2026-0001","info":{"name":"Example CVE","severity":"High",'
        '"description":"Details","remediation":"Patch","classification":{"cve-id":["CVE-2026-0001"],'
        '"cvss-score":8.1}},"matched-at":"https://app.example.com"}'
    )

    assert len(findings) == 1
    assert findings[0].severity == 'high'
    assert findings[0].cve == 'CVE-2026-0001'
    assert findings[0].cvss_score == 8.1
