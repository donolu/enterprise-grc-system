from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate

from core.models import AuditEvent
from vendors.models import Vendor, VendorTask
from vendors.views import VendorTaskViewSet, VendorViewSet


User = get_user_model()


class VendorWorkflowAuditTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='vendor.admin',
            email='vendor.admin@example.com',
            password='testpass123',
        )
        self.factory = APIRequestFactory()
        self.vendor = Vendor.objects.create(
            name='Cloud Provider',
            status='under_review',
            risk_level='medium',
            created_by=self.user,
            assigned_to=self.user,
        )
        self.task = VendorTask.objects.create(
            vendor=self.vendor,
            task_type='security_review',
            title='Review SOC 2 report',
            due_date=date.today() + timedelta(days=30),
            assigned_to=self.user,
            created_by=self.user,
        )

    def test_vendor_status_update_writes_standard_audit_payload(self):
        request = self.factory.post(
            f'/api/vendors/vendors/{self.vendor.id}/update_status/',
            {'status': 'approved', 'note': 'Security review accepted.'},
            format='json',
        )
        force_authenticate(request, user=self.user)

        response = VendorViewSet.as_view({'post': 'update_status'})(request, pk=self.vendor.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event = AuditEvent.objects.get(event='VENDOR_STATUS_UPDATED')
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.details['actor']['email'], self.user.email)
        self.assertEqual(event.details['object']['type'], 'vendors.Vendor')
        self.assertEqual(event.details['object']['display'], self.vendor.vendor_id)
        self.assertEqual(event.details['previous']['status'], 'under_review')
        self.assertEqual(event.details['new']['status'], 'approved')
        self.assertEqual(event.details['reason'], 'Security review accepted.')

    def test_vendor_task_status_update_audits_previous_and_new_values(self):
        request = self.factory.post(
            f'/api/vendors/tasks/{self.task.id}/update_status/',
            {
                'status': 'completed',
                'completion_notes': 'SOC 2 report reviewed.',
            },
            format='json',
        )
        force_authenticate(request, user=self.user)

        response = VendorTaskViewSet.as_view({'post': 'update_status'})(
            request,
            pk=self.task.id,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event = AuditEvent.objects.get(event='VENDOR_TASK_STATUS_UPDATED')
        self.assertEqual(event.details['previous']['status'], 'pending')
        self.assertEqual(event.details['new']['status'], 'completed')
        self.assertEqual(event.details['actor']['id'], str(self.user.id))
        self.assertNotIn('SOC 2 report reviewed.', str(event.details['new']))

    def test_vendor_task_bulk_update_is_audited_per_task(self):
        second_task = VendorTask.objects.create(
            vendor=self.vendor,
            task_type='contract_renewal',
            title='Renew service contract',
            due_date=date.today() + timedelta(days=45),
            created_by=self.user,
        )
        request = self.factory.post(
            '/api/vendors/tasks/bulk_action/',
            {
                'task_ids': [self.task.id, second_task.id],
                'action': 'update_priority',
                'priority': 'critical',
            },
            format='json',
        )
        force_authenticate(request, user=self.user)

        response = VendorTaskViewSet.as_view({'post': 'bulk_action'})(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        events = AuditEvent.objects.filter(event='VENDOR_TASK_BULK_UPDATED')
        self.assertEqual(events.count(), 2)
        for event in events:
            self.assertEqual(event.details['previous']['priority'], 'medium')
            self.assertEqual(event.details['new']['priority'], 'critical')
            self.assertEqual(event.details['source']['reference'], 'vendor_task.bulk_action.update_priority')
