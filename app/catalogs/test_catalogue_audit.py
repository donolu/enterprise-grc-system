from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate

from core.models import AuditEvent

from .models import (
    AssessmentEvidence,
    Clause,
    Control,
    ControlAssessment,
    ControlEvidence,
    Framework,
)
from .views import AssessmentEvidenceViewSet, ControlAssessmentViewSet, FrameworkViewSet


User = get_user_model()


class CatalogueAuditAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='auditor',
            email='auditor@example.com',
            password='testpass123',
        )
        self.factory = APIRequestFactory()
        self.framework = Framework.objects.create(
            name='ISO 27001',
            short_name='ISO27001',
            version='2022',
            description='Information security management',
            framework_type='security',
            issuing_organization='ISO',
            effective_date=date.today(),
            status='active',
            created_by=self.user,
        )
        self.clause = Clause.objects.create(
            framework=self.framework,
            clause_id='A.5.1',
            title='Policies for information security',
            description='Policies shall be defined and approved.',
        )
        self.control = Control.objects.create(
            control_id='ISO-A.5.1',
            name='Information security policy',
            description='Maintain an approved information security policy.',
            control_type='administrative',
            created_by=self.user,
        )
        self.control.clauses.add(self.clause)
        self.assessment = ControlAssessment.objects.create(
            framework=self.framework,
            control=self.control,
            applicability='to_be_determined',
            implementation_status='not_implemented',
            status='not_started',
            due_date=date.today() + timedelta(days=30),
            created_by=self.user,
        )

    def test_framework_update_writes_standard_audit_payload(self):
        request = self.factory.patch(
            f'/api/catalogs/api/frameworks/{self.framework.id}/',
            {'status': 'deprecated'},
            format='json',
        )
        force_authenticate(request, user=self.user)
        response = FrameworkViewSet.as_view({'patch': 'partial_update'})(
            request,
            pk=self.framework.id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event = AuditEvent.objects.get(event='CATALOGUE_FRAMEWORK_UPDATED')
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.details['actor']['email'], self.user.email)
        self.assertEqual(event.details['object']['type'], 'catalogs.Framework')
        self.assertEqual(event.details['object']['id'], str(self.framework.id))
        self.assertEqual(event.details['object']['display'], 'ISO27001 v2022')
        self.assertEqual(event.details['previous'], {'status': 'active'})
        self.assertEqual(event.details['new'], {'status': 'deprecated'})
        self.assertEqual(event.details['source']['type'], 'api')

    def test_assessment_status_change_audits_framework_snapshot(self):
        request = self.factory.post(
            f'/api/catalogs/api/assessments/{self.assessment.id}/update_status/',
            {'status': 'in_progress', 'notes': 'Started owner review'},
            format='json',
        )
        force_authenticate(request, user=self.user)
        response = ControlAssessmentViewSet.as_view({'post': 'update_status'})(
            request,
            pk=self.assessment.id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event = AuditEvent.objects.get(event='CONTROL_ASSESSMENT_STATUS_UPDATED')
        self.assertEqual(event.details['object']['type'], 'catalogs.ControlAssessment')
        self.assertEqual(event.details['new']['status'], 'in_progress')
        self.assertEqual(event.details['framework_id'], self.framework.id)
        self.assertEqual(event.details['framework_version'], self.framework.version)
        self.assertEqual(event.details['reason'], 'Started owner review')

    def test_evidence_link_create_and_delete_are_audited(self):
        evidence = ControlEvidence.objects.create(
            control=self.control,
            title='Policy document',
            evidence_type='document',
            collected_by=self.user,
        )

        request = self.factory.post(
            '/api/catalogs/api/assessment-evidence/',
            {
                'assessment': self.assessment.id,
                'evidence': evidence.id,
                'evidence_purpose': 'Policy evidence',
                'is_primary_evidence': True,
            },
            format='json',
        )
        force_authenticate(request, user=self.user)
        create_response = AssessmentEvidenceViewSet.as_view({'post': 'create'})(request)
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        link = AssessmentEvidence.objects.get()
        linked = AuditEvent.objects.get(event='ASSESSMENT_EVIDENCE_LINKED')
        self.assertEqual(linked.details['object']['id'], str(link.id))
        self.assertEqual(linked.details['new']['assessment_id'], self.assessment.id)
        self.assertTrue(linked.details['new']['is_primary_evidence'])

        request = self.factory.delete(f'/api/catalogs/api/assessment-evidence/{link.id}/')
        force_authenticate(request, user=self.user)
        delete_response = AssessmentEvidenceViewSet.as_view({'delete': 'destroy'})(
            request,
            pk=link.id,
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        unlinked = AuditEvent.objects.get(event='ASSESSMENT_EVIDENCE_UNLINKED')
        self.assertEqual(unlinked.details['previous']['evidence_id'], evidence.id)

    def test_bulk_assessments_can_coexist_for_framework_versions(self):
        next_framework = Framework.objects.create(
            name=self.framework.name,
            short_name=self.framework.short_name,
            version='2024',
            description='Updated information security management',
            framework_type='security',
            issuing_organization='ISO',
            effective_date=date.today(),
            status='active',
            created_by=self.user,
        )
        next_clause = Clause.objects.create(
            framework=next_framework,
            clause_id=self.clause.clause_id,
            title=self.clause.title,
            description='Updated control wording.',
        )
        self.control.clauses.add(next_clause)
        self.assessment.delete()

        request = self.factory.post(
            '/api/catalogs/api/assessments/bulk_create/',
            {'framework_id': self.framework.id},
            format='json',
        )
        force_authenticate(request, user=self.user)
        first_response = ControlAssessmentViewSet.as_view({'post': 'bulk_create'})(request)
        request = self.factory.post(
            '/api/catalogs/api/assessments/bulk_create/',
            {'framework_id': next_framework.id},
            format='json',
        )
        force_authenticate(request, user=self.user)
        second_response = ControlAssessmentViewSet.as_view({'post': 'bulk_create'})(request)

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            list(
                ControlAssessment.objects.order_by('framework__version')
                .values_list('framework__version', flat=True)
            ),
            ['2022', '2024'],
        )
        self.assertEqual(
            AuditEvent.objects.filter(event='CONTROL_ASSESSMENTS_BULK_CREATED').count(),
            2,
        )
