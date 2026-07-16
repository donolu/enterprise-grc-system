from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django_tenants.utils import tenant_context

from policies.models import Policy, PolicyCategory, PolicyVersion, PolicyVersionAuditLog

User = get_user_model()


@pytest.fixture
def policy_users(test_tenant):
    with tenant_context(test_tenant):
        owner = User.objects.create_user(
            username='policy-owner',
            email='policy-owner@example.com',
            password='testpass123',
        )
        normal = User.objects.create_user(
            username='normal-user',
            email='normal@example.com',
            password='testpass123',
        )
    return owner, normal


@pytest.fixture
def policy_version(test_tenant, policy_users):
    owner, _ = policy_users
    with tenant_context(test_tenant):
        category = PolicyCategory.objects.create(name='Security')
        policy = Policy.objects.create(
            title='Access Control Policy',
            category=category,
            policy_type='policy',
            owner=owner,
            created_by=owner,
            next_review_date=timezone.now().date() + timedelta(days=90),
        )
        version = PolicyVersion.objects.create(
            policy=policy,
            version_number='1.0',
            document=SimpleUploadedFile(
                'access-control.pdf',
                b'%PDF-1.4\nsource pdf\n%%EOF',
                content_type='application/pdf',
            ),
            created_by=owner,
            approved_at=timezone.now(),
            approved_by=owner,
            lifecycle_state='approved',
        )
    return version


@pytest.mark.django_db
def test_finalize_pdf_source_creates_final_pdf_and_audit_log(
    tenant_client,
    test_tenant,
    policy_users,
    policy_version,
):
    owner, _ = policy_users
    tenant_client.defaults['HTTP_HOST'] = f'{test_tenant.schema_name}.localhost'
    tenant_client.force_authenticate(user=owner)

    response = tenant_client.post(f'/api/policies/versions/{policy_version.id}/finalize/')

    assert response.status_code == 200
    policy_version.refresh_from_db()
    assert policy_version.lifecycle_state == 'final'
    assert policy_version.final_pdf.name.endswith('_final.pdf')
    assert PolicyVersionAuditLog.objects.filter(
        policy_version=policy_version,
        action='finalized',
    ).exists()
    audit_log = PolicyVersionAuditLog.objects.get(
        policy_version=policy_version,
        action='finalized',
    )
    assert audit_log.details['actor']['email'] == owner.email
    assert audit_log.details['object']['type'] == 'policies.PolicyVersion'
    assert audit_log.details['object']['id'] == str(policy_version.id)
    assert audit_log.details['event'] == 'POLICY_VERSION_FINALIZED'
    assert audit_log.details['previous']['lifecycle_state'] == 'approved'
    assert audit_log.details['new']['lifecycle_state'] == 'final'
    assert audit_log.details['source']['type'] == 'conversion'
    assert 'source pdf' not in str(audit_log.details)


@pytest.mark.django_db
def test_finalized_normal_download_serves_pdf_and_blocks_source(
    tenant_client,
    test_tenant,
    policy_users,
    policy_version,
):
    owner, normal = policy_users
    with tenant_context(test_tenant):
        policy_version.lifecycle_state = 'final'
        policy_version.finalized_at = timezone.now()
        policy_version.finalized_by = owner
        policy_version.final_pdf.save(
            'final-policy.pdf',
            SimpleUploadedFile('final-policy.pdf', b'%PDF-1.4\nfinal\n%%EOF'),
            save=True,
        )

    tenant_client.defaults['HTTP_HOST'] = f'{test_tenant.schema_name}.localhost'
    tenant_client.force_authenticate(user=normal)

    pdf_response = tenant_client.get(f'/api/policies/versions/{policy_version.id}/download/')
    source_response = tenant_client.get(f'/api/policies/versions/{policy_version.id}/download-source/')

    assert pdf_response.status_code == 200
    assert 'POL-SEC-001_v1.0.pdf' in pdf_response['Content-Disposition']
    assert source_response.status_code == 403
    assert PolicyVersionAuditLog.objects.filter(
        policy_version=policy_version,
        action='downloaded_pdf',
    ).exists()
    pdf_audit_log = PolicyVersionAuditLog.objects.get(
        policy_version=policy_version,
        action='downloaded_pdf',
    )
    assert pdf_audit_log.details['event'] == 'POLICY_VERSION_DOWNLOADED_PDF'
    assert pdf_audit_log.details['source']['reference'] == 'final_pdf'


@pytest.mark.django_db
def test_authorised_editor_can_download_source(
    tenant_client,
    test_tenant,
    policy_users,
    policy_version,
):
    owner, _ = policy_users
    tenant_client.defaults['HTTP_HOST'] = f'{test_tenant.schema_name}.localhost'
    tenant_client.force_authenticate(user=owner)

    response = tenant_client.get(f'/api/policies/versions/{policy_version.id}/download-source/')

    assert response.status_code == 200
    assert 'access-control.pdf' in response['Content-Disposition']
    assert PolicyVersionAuditLog.objects.filter(
        policy_version=policy_version,
        action='downloaded_source',
    ).exists()
    source_audit_log = PolicyVersionAuditLog.objects.get(
        policy_version=policy_version,
        action='downloaded_source',
    )
    assert source_audit_log.details['event'] == 'POLICY_VERSION_DOWNLOADED_SOURCE'
    assert source_audit_log.details['source']['reference'] == 'source_document'


@pytest.mark.django_db
def test_docx_finalization_failure_is_audited(tenant_client, test_tenant, policy_users):
    owner, _ = policy_users
    with tenant_context(test_tenant):
        category = PolicyCategory.objects.create(name='Continuity')
        policy = Policy.objects.create(
            title='Continuity Policy',
            category=category,
            policy_type='policy',
            owner=owner,
            created_by=owner,
            next_review_date=timezone.now().date() + timedelta(days=90),
        )
        version = PolicyVersion.objects.create(
            policy=policy,
            version_number='1.0',
            document=SimpleUploadedFile(
                'continuity.docx',
                b'not a real docx',
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            ),
            created_by=owner,
            approved_at=timezone.now(),
            approved_by=owner,
            lifecycle_state='approved',
        )

    tenant_client.defaults['HTTP_HOST'] = f'{test_tenant.schema_name}.localhost'
    tenant_client.force_authenticate(user=owner)

    response = tenant_client.post(f'/api/policies/versions/{version.id}/finalize/')

    assert response.status_code == 503
    assert PolicyVersionAuditLog.objects.filter(
        policy_version=version,
        action='conversion_failed',
    ).exists()
    audit_log = PolicyVersionAuditLog.objects.get(
        policy_version=version,
        action='conversion_failed',
    )
    assert audit_log.details['event'] == 'POLICY_VERSION_CONVERSION_FAILED'
    assert audit_log.details['source']['type'] == 'conversion'


@pytest.mark.django_db
def test_finalized_version_cannot_replace_source_document(
    tenant_client,
    test_tenant,
    policy_users,
    policy_version,
):
    owner, _ = policy_users
    with tenant_context(test_tenant):
        policy_version.lifecycle_state = 'final'
        policy_version.save(update_fields=['lifecycle_state'])

    tenant_client.defaults['HTTP_HOST'] = f'{test_tenant.schema_name}.localhost'
    tenant_client.force_authenticate(user=owner)

    response = tenant_client.patch(
        f'/api/policies/versions/{policy_version.id}/',
        {'document': SimpleUploadedFile('replacement.pdf', b'%PDF-1.4\nreplacement\n%%EOF')},
        format='multipart',
    )

    assert response.status_code == 400
    assert 'document' in response.json()


@pytest.mark.django_db
def test_policy_distribution_and_acknowledgment_are_audited(
    tenant_client,
    test_tenant,
    policy_users,
    policy_version,
):
    owner, normal = policy_users
    with tenant_context(test_tenant):
        policy_version.is_active = True
        policy_version.is_published = True
        policy_version.lifecycle_state = 'final'
        policy_version.save(update_fields=['is_active', 'is_published', 'lifecycle_state'])

    tenant_client.defaults['HTTP_HOST'] = f'{test_tenant.schema_name}.localhost'
    tenant_client.force_authenticate(user=owner)
    distribute_response = tenant_client.post(
        f'/api/policies/policies/{policy_version.policy.id}/distribute/',
        {'user_ids': [normal.id]},
        format='json',
    )

    assert distribute_response.status_code == 201
    distribute_log = PolicyVersionAuditLog.objects.get(
        policy_version=policy_version,
        action='distributed',
    )
    assert distribute_log.details['event'] == 'POLICY_VERSION_DISTRIBUTED'
    assert distribute_log.details['new']['distribution_count'] == 1
    assert distribute_log.details['new']['recipient_ids'] == [str(normal.id)]

    tenant_client.force_authenticate(user=normal)
    acknowledge_response = tenant_client.post(
        f'/api/policies/policies/{policy_version.policy.id}/acknowledge/'
    )

    assert acknowledge_response.status_code == 201
    acknowledgment_log = PolicyVersionAuditLog.objects.get(
        policy_version=policy_version,
        action='acknowledged',
    )
    assert acknowledgment_log.details['event'] == 'POLICY_VERSION_ACKNOWLEDGED'
    assert acknowledgment_log.details['actor']['email'] == normal.email
    assert acknowledgment_log.details['new']['acknowledgment_id']
