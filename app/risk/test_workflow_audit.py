from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate

from core.models import AuditEvent
from risk.models import Risk, RiskAction
from risk.views import RiskActionViewSet, RiskViewSet


User = get_user_model()


class RiskWorkflowAuditTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='risk.admin',
            email='risk.admin@example.com',
            password='testpass123',
        )
        self.factory = APIRequestFactory()
        self.risk = Risk.objects.create(
            risk_id='RISK-AUD-001',
            title='Data leakage risk',
            description='Customer records may be exposed.',
            impact=4,
            likelihood=3,
            risk_owner=self.user,
            created_by=self.user,
        )
        self.action = RiskAction.objects.create(
            risk=self.risk,
            title='Review access controls',
            description='Review privileged access.',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=30),
            created_by=self.user,
        )

    def test_risk_status_update_writes_standard_audit_payload(self):
        request = self.factory.post(
            f'/api/risk/risks/{self.risk.id}/update_status/',
            {
                'status': 'treatment_planned',
                'treatment_strategy': 'mitigate',
                'note': 'Treatment agreed by the risk owner.',
            },
            format='json',
        )
        force_authenticate(request, user=self.user)

        response = RiskViewSet.as_view({'post': 'update_status'})(request, pk=self.risk.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event = AuditEvent.objects.get(event='RISK_STATUS_UPDATED')
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.details['actor']['email'], self.user.email)
        self.assertEqual(event.details['object']['type'], 'risk.Risk')
        self.assertEqual(event.details['object']['display'], 'RISK-AUD-001')
        self.assertEqual(event.details['previous']['status'], 'identified')
        self.assertEqual(event.details['new']['status'], 'treatment_planned')
        self.assertEqual(event.details['new']['treatment_strategy'], 'mitigate')
        self.assertEqual(event.details['source']['type'], 'api')

    @patch('risk.notifications.RiskActionNotificationService.notify_evidence_uploaded')
    def test_action_evidence_upload_is_audited_without_file_contents(self, mock_notify):
        request = self.factory.post(
            f'/api/risk/actions/{self.action.id}/upload_evidence/',
            {
                'title': 'Remediation screenshot',
                'evidence_type': 'screenshot',
                'external_link': 'https://example.com/evidence/remediation',
            },
            format='multipart',
        )
        force_authenticate(request, user=self.user)

        response = RiskActionViewSet.as_view({'post': 'upload_evidence'})(
            request,
            pk=self.action.id,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_notify.assert_called_once()
        event = AuditEvent.objects.get(event='RISK_ACTION_EVIDENCE_UPLOADED')
        self.assertEqual(event.details['actor']['email'], self.user.email)
        self.assertEqual(event.details['object']['type'], 'risk.RiskActionEvidence')
        self.assertEqual(event.details['new']['title'], 'Remediation screenshot')
        self.assertEqual(event.details['new']['evidence_type'], 'screenshot')
        self.assertEqual(event.details['new']['file'], {'present': False, 'name': ''})
        self.assertNotIn('file_content', event.details['new'])

    @patch('risk.notifications.RiskActionNotificationService.notify_status_change')
    def test_action_status_update_captures_actor_and_previous_values(self, mock_notify):
        request = self.factory.post(
            f'/api/risk/actions/{self.action.id}/update_status/',
            {
                'status': 'completed',
                'note': 'Remediation finished.',
            },
            format='json',
        )
        force_authenticate(request, user=self.user)

        response = RiskActionViewSet.as_view({'post': 'update_status'})(
            request,
            pk=self.action.id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_notify.assert_called_once()
        event = AuditEvent.objects.get(event='RISK_ACTION_STATUS_UPDATED')
        self.assertEqual(event.details['previous']['status'], 'pending')
        self.assertEqual(event.details['new']['status'], 'completed')
        self.assertEqual(event.details['new']['progress_percentage'], 100)
        self.assertEqual(event.details['actor']['id'], str(self.user.id))
