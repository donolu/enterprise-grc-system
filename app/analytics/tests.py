from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase
from django.urls import reverse
from django_tenants.utils import schema_context, tenant_context
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from analytics.operator import OperatorProductAnalyticsService
from analytics.views import operator_usage_dashboard
from core.models import AuditEvent, Document, Domain, Plan, Subscription, Tenant
from exports.models import TenantDataExport

User = get_user_model()


class OperatorProductAnalyticsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.factory = APIRequestFactory()
        with schema_context('public'):
            self.free_plan = Plan.objects.create(
                name='Free',
                slug='free',
                price_monthly=0,
                included_modules=['frameworks'],
            )
            self.basic_plan = Plan.objects.create(
                name='Basic',
                slug='basic',
                price_monthly=49,
                included_modules=['frameworks', 'risk', 'exports'],
            )
            self.tenant_a = self._create_tenant('tenant_a_analytics', 'tenant-a-analytics', 'Tenant A')
            self.tenant_b = self._create_tenant('tenant_b_analytics', 'tenant-b-analytics', 'Tenant B')
            Subscription.objects.create(
                tenant=self.tenant_a,
                plan=self.basic_plan,
                status='active',
                enabled_modules=['frameworks', 'risk', 'exports'],
            )
            Subscription.objects.create(
                tenant=self.tenant_b,
                plan=self.free_plan,
                status='trialing',
                trial_module='frameworks',
            )
            self.public_operator = User.objects.create_superuser(
                username='public-operator',
                email='operator@axim.test',
                password='testpass123',
            )

        self.tenant_staff = self._create_user(self.tenant_a, 'operator', is_staff=True)
        self.normal_user = self._create_user(self.tenant_a, 'normal', is_staff=False)
        tenant_b_user = self._create_user(self.tenant_b, 'tenantb', is_staff=False)

        with tenant_context(self.tenant_a):
            document = Document(
                title='Confidential acquisition plan',
                uploaded_by=self.tenant_staff,
                mime_type='text/plain',
            )
            document.file.save('confidential-plan.txt', ContentFile(b'classified'), save=True)
            TenantDataExport.objects.create(
                title='Secret audit export',
                export_format='xlsx',
                requested_by=self.tenant_staff,
            )
            AuditEvent.objects.create(
                user=self.tenant_staff,
                event='SECRET_CUSTOMER_WORKFLOW',
                details={'document_title': 'Confidential acquisition plan'},
            )

        with tenant_context(self.tenant_b):
            AuditEvent.objects.create(
                user=tenant_b_user,
                event='TENANT_B_ACTIVITY',
                details={'sensitive': 'do not expose'},
            )

    def test_operator_dashboard_aggregates_usage_without_tenant_content(self):
        dashboard = OperatorProductAnalyticsService().build_dashboard()

        self.assertEqual(dashboard['summary']['total_tenants'], 2)
        self.assertEqual(dashboard['summary']['active_tenants'], 2)
        self.assertEqual(dashboard['summary']['trial_tenants'], 1)
        self.assertEqual(dashboard['summary']['paid_active_tenants'], 1)
        self.assertEqual(dashboard['usage_totals']['document_uploads'], 1)
        self.assertEqual(dashboard['usage_totals']['data_exports'], 1)
        self.assertEqual(dashboard['usage_totals']['audit_events'], 2)

        module_counts = {
            module['module_key']: module['tenant_count']
            for module in dashboard['module_adoption']
        }
        self.assertEqual(module_counts['frameworks'], 2)
        self.assertEqual(module_counts['risk'], 1)

        response_text = str(dashboard)
        self.assertNotIn('Confidential acquisition plan', response_text)
        self.assertNotIn('Secret audit export', response_text)
        self.assertNotIn('do not expose', response_text)
        self.assertTrue(dashboard['privacy']['tenant_content_excluded'])

    def test_operator_endpoint_requires_staff_user(self):
        self.client.defaults['HTTP_HOST'] = self.tenant_a_domain
        self.client.force_authenticate(user=self.normal_user)

        response = self.client.get(reverse('analytics:operator_usage_dashboard'))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_operator_endpoint_rejects_tenant_staff_user(self):
        self.client.defaults['HTTP_HOST'] = self.tenant_a_domain
        self.client.force_authenticate(user=self.tenant_staff)

        response = self.client.get(reverse('analytics:operator_usage_dashboard'))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_operator_endpoint_returns_json_and_csv(self):
        response = self._operator_request({'days': '30'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['summary']['total_tenants'], 2)

        csv_response = self._operator_request({'export': 'csv'})

        self.assertEqual(csv_response.status_code, status.HTTP_200_OK)
        self.assertEqual(csv_response['Content-Type'], 'text/csv')
        csv_content = csv_response.content.decode('utf-8')
        self.assertIn('tenant_slug', csv_content)
        self.assertNotIn('Confidential acquisition plan', csv_content)

    def _create_tenant(self, schema_name, slug, name):
        tenant = Tenant.objects.create(schema_name=schema_name, slug=slug, name=name)
        domain = Domain.objects.create(
            tenant=tenant,
            domain=f'{slug}.localhost',
            is_primary=True,
        )
        if slug == 'tenant-a-analytics':
            self.tenant_a_domain = domain.domain
        return tenant

    def _create_user(self, tenant, username, is_staff):
        with tenant_context(tenant):
            return User.objects.create_user(
                username=username,
                email=f'{username}@example.com',
                password='testpass123',
                is_staff=is_staff,
            )

    def _operator_request(self, query_params):
        request = self.factory.get('/api/analytics/operator/usage/', query_params)
        request.tenant = SimpleNamespace(schema_name='public')
        force_authenticate(request, user=self.public_operator)
        return operator_usage_dashboard(request)
