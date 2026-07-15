from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import (
    GovernanceArtefact,
    ManagementReview,
    NonConformity,
    RegulatoryRequirement,
)

User = get_user_model()


def response_results(payload):
    return payload.get('results', payload) if isinstance(payload, dict) else payload


class ComplianceGovernanceAPITest(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.defaults['HTTP_HOST'] = self.domain.domain
        self.user = User.objects.create_user(
            username='compliance.owner',
            email='compliance.owner@example.com',
            password='testpass123',
        )
        self.client.force_authenticate(user=self.user)

    def test_regulatory_requirement_crud_and_links_to_artefact(self):
        artefact = GovernanceArtefact.objects.create(
            title='Legal and regulatory obligations register',
            artefact_type='regulatory_contractual_sheet',
            owner=self.user,
            created_by=self.user,
        )

        response = self.client.post(
            reverse('compliance:regulatory-requirements-list'),
            {
                'title': 'UK GDPR Article 30 record of processing activities',
                'source_type': 'regulation',
                'issuing_body': 'Information Commissioner Office',
                'jurisdiction': 'United Kingdom',
                'reference': 'UK GDPR Article 30',
                'description': 'Maintain records of processing activities.',
                'applicability_status': 'applicable',
                'compliance_status': 'in_progress',
                'priority': 'high',
                'owner': self.user.id,
                'next_review_date': '2026-09-30',
                'linked_artefacts': [artefact.id],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['requirement_id'].startswith('REQ-'))
        requirement = RegulatoryRequirement.objects.get()
        self.assertEqual(requirement.created_by, self.user)
        self.assertEqual(requirement.linked_artefacts.get(), artefact)

        list_response = self.client.get(
            reverse('compliance:regulatory-requirements-list'),
            {'search': 'GDPR', 'compliance_status': 'in_progress'},
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(response_results(list_response.data)[0]['title'], requirement.title)

    def test_nonconformity_sets_closed_date_and_exposes_overdue_flag(self):
        requirement = RegulatoryRequirement.objects.create(
            title='Maintain internal audit programme',
            source_type='standard',
            applicability_status='applicable',
            owner=self.user,
            created_by=self.user,
        )
        nonconformity = NonConformity.objects.create(
            title='Internal audit actions overdue',
            description='Several audit findings have no owner updates.',
            severity='major',
            status='open',
            source_type='internal_audit',
            due_date=timezone.now().date() - timedelta(days=1),
            owner=self.user,
            raised_by=self.user,
            regulatory_requirement=requirement,
        )

        self.assertTrue(nonconformity.is_overdue)

        response = self.client.patch(
            reverse('compliance:non-conformities-detail', kwargs={'pk': nonconformity.id}),
            {'status': 'closed'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        nonconformity.refresh_from_db()
        self.assertIsNotNone(nonconformity.closed_on)
        self.assertFalse(nonconformity.is_overdue)

    def test_management_review_links_requirements_nonconformities_and_artefacts(self):
        artefact = GovernanceArtefact.objects.create(
            title='ISO management review agenda',
            artefact_type='agenda',
            owner=self.user,
            created_by=self.user,
        )
        requirement = RegulatoryRequirement.objects.create(
            title='Annual information security management review',
            source_type='standard',
            applicability_status='applicable',
            owner=self.user,
            created_by=self.user,
        )
        nonconformity = NonConformity.objects.create(
            title='Previous review action still open',
            description='Action owner missed the agreed completion date.',
            severity='minor',
            owner=self.user,
            raised_by=self.user,
        )

        response = self.client.post(
            reverse('compliance:management-reviews-list'),
            {
                'title': 'Q3 ISO management review',
                'status': 'held',
                'meeting_date': '2026-10-15',
                'period_start': '2026-07-01',
                'period_end': '2026-09-30',
                'chair': self.user.id,
                'attendees': [self.user.id],
                'agenda': 'Review ISMS performance, non-conformities and metrics.',
                'minutes': 'Reviewed open actions and agreed owners.',
                'decisions': 'Continue monthly control metrics review.',
                'actions_summary': 'Two actions carried forward.',
                'inputs': {'risk_summary': 'No critical risks open'},
                'outputs': {'approved_changes': ['Update scope statement']},
                'linked_requirements': [requirement.id],
                'linked_nonconformities': [nonconformity.id],
                'linked_artefacts': [artefact.id],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        review = ManagementReview.objects.get()
        self.assertTrue(review.review_id.startswith('MR-'))
        self.assertEqual(review.created_by, self.user)
        self.assertEqual(review.attendees.get(), self.user)
        self.assertEqual(review.linked_requirements.get(), requirement)
        self.assertEqual(review.linked_nonconformities.get(), nonconformity)
        self.assertEqual(review.linked_artefacts.get(), artefact)
