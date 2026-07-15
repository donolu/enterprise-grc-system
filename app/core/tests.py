"""
Tests for core application functionality.
"""

from datetime import timedelta

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django_tenants.utils import tenant_context, schema_context
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import Tenant, Domain, Plan, Subscription, Document, LimitOverrideRequest
from billing.entitlements import ALL_MODULE_KEYS
from billing.services import PlanEnforcementService

User = get_user_model()


class TenantModelTest(TestCase):
    """Test Tenant model functionality."""
    
    def setUp(self):
        self.tenant = Tenant(
            name="Test Company",
            slug="test",
            schema_name="test_company"
        )
    
    def test_tenant_creation(self):
        """Test tenant can be created with required fields."""
        self.tenant.save()
        self.assertEqual(self.tenant.name, "Test Company")
        self.assertEqual(self.tenant.slug, "test")
        self.assertEqual(self.tenant.schema_name, "test_company")
    
    def test_tenant_str_representation(self):
        """Test tenant string representation."""
        self.tenant.save()
        expected = "Test Company (test_company)"
        self.assertEqual(str(self.tenant), expected)


class PlanModelTest(TestCase):
    """Test Plan model functionality."""
    
    def setUp(self):
        self.plan = Plan(
            name="Basic",
            slug="basic",
            description="Basic plan",
            price_monthly=49.99,
            max_users=10,
            max_documents=500,
            max_frameworks=5,
            has_api_access=True
        )
    
    def test_plan_creation(self):
        """Test plan can be created with required fields."""
        self.plan.save()
        self.assertEqual(self.plan.name, "Basic")
        self.assertEqual(self.plan.price_monthly, 49.99)
        self.assertTrue(self.plan.has_api_access)
    
    def test_plan_str_representation(self):
        """Test plan string representation."""
        self.plan.save()
        expected = "Basic ($49.99/month)"
        self.assertEqual(str(self.plan), expected)


class SubscriptionModelTest(TestCase):
    """Test Subscription model functionality."""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Company",
            slug="test", 
            schema_name="test_sub"
        )
        self.plan = Plan.objects.create(
            name="Free",
            slug="free",
            price_monthly=0,
            max_users=3,
            max_documents=50
        )
        self.subscription = Subscription(
            tenant=self.tenant,
            plan=self.plan,
            status="active"
        )
    
    def test_subscription_creation(self):
        """Test subscription can be created."""
        self.subscription.save()
        self.assertEqual(self.subscription.tenant, self.tenant)
        self.assertEqual(self.subscription.plan, self.plan)
        self.assertTrue(self.subscription.is_active)
    
    def test_effective_limits_without_overrides(self):
        """Test effective limits use plan defaults when no overrides."""
        self.subscription.save()
        self.assertEqual(self.subscription.get_effective_user_limit(), 3)
        self.assertEqual(self.subscription.get_effective_document_limit(), 50)
    
    def test_effective_limits_with_overrides(self):
        """Test effective limits use custom overrides when set."""
        self.subscription.custom_max_users = 15
        self.subscription.custom_max_documents = 200
        self.subscription.save()
        
        self.assertEqual(self.subscription.get_effective_user_limit(), 15)
        self.assertEqual(self.subscription.get_effective_document_limit(), 200)

    def test_enterprise_subscription_gets_all_modules(self):
        enterprise_plan = Plan.objects.create(
            name="Enterprise",
            slug="enterprise",
            price_monthly=199,
        )
        subscription = Subscription.objects.create(
            tenant=self.tenant,
            plan=enterprise_plan,
            status="active",
        )

        self.assertEqual(subscription.get_enabled_modules(), list(ALL_MODULE_KEYS))

    def test_trial_subscription_is_restricted_to_one_module(self):
        self.plan.included_modules = ["frameworks", "risk"]
        self.plan.save()
        self.subscription.status = "trialing"
        self.subscription.enabled_modules = ["frameworks", "risk"]
        self.subscription.trial_module = "risk"
        self.subscription.trial_start = timezone.now()
        self.subscription.trial_end = timezone.now() + timedelta(days=30)
        self.subscription.save()

        self.assertEqual(self.subscription.get_enabled_modules(), ["risk"])

    def test_expired_trial_has_no_enabled_modules(self):
        self.subscription.status = "trialing"
        self.subscription.trial_module = "risk"
        self.subscription.trial_start = timezone.now() - timedelta(days=60)
        self.subscription.trial_end = timezone.now() - timedelta(days=30)
        self.subscription.save()

        self.assertEqual(self.subscription.get_enabled_modules(), [])


@pytest.mark.django_db
class TestPlanEnforcementService:
    """Test PlanEnforcementService functionality."""
    
    def test_check_feature_access_with_permission(self, test_tenant, basic_plan):
        """Test feature access check when user has permission."""
        with schema_context("public"):
            Subscription.objects.create(
                tenant=test_tenant,
                plan=basic_plan,
                status="active"
            )
        
        has_access, error = PlanEnforcementService.check_feature_access(
            test_tenant, 'has_api_access'
        )
        
        assert has_access is True
        assert error is None
    
    def test_check_feature_access_without_permission(self, test_tenant, free_plan):
        """Test feature access check when user lacks permission."""
        with schema_context("public"):
            Subscription.objects.create(
                tenant=test_tenant,
                plan=free_plan,
                status="active"
            )
        
        has_access, error = PlanEnforcementService.check_feature_access(
            test_tenant, 'has_api_access'
        )
        
        assert has_access is False
        assert "not available" in error


class LimitOverrideRequestTest(TestCase):
    """Test LimitOverrideRequest model functionality."""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Company",
            slug="test",
            schema_name="test_override"
        )
        self.plan = Plan.objects.create(
            name="Free",
            slug="free", 
            price_monthly=0,
            max_users=3
        )
        self.subscription = Subscription.objects.create(
            tenant=self.tenant,
            plan=self.plan,
            status="active"
        )
        self.override_request = LimitOverrideRequest(
            subscription=self.subscription,
            limit_type="max_users",
            current_limit=3,
            requested_limit=10,
            business_justification="Need more users for project expansion",
            requested_by="test@example.com"
        )
    
    def test_override_request_creation(self):
        """Test override request can be created."""
        self.override_request.save()
        self.assertEqual(self.override_request.subscription, self.subscription)
        self.assertEqual(self.override_request.requested_limit, 10)
        self.assertTrue(self.override_request.needs_first_approval)
    
    def test_first_approval_process(self):
        """Test first approval process."""
        self.override_request.save()
        
        success = self.override_request.approve_first(
            "approver1@example.com", 
            "Approved for business growth"
        )
        
        self.assertTrue(success)
        self.assertFalse(self.override_request.needs_first_approval)
        self.assertTrue(self.override_request.needs_second_approval)
    
    def test_second_approval_process(self):
        """Test second approval process."""
        self.override_request.save()
        
        # First approval
        self.override_request.approve_first("approver1@example.com")
        
        # Second approval
        success = self.override_request.approve_second(
            "approver2@example.com",
            "Second approval granted"
        )
        
        self.assertTrue(success)
        self.assertTrue(self.override_request.is_fully_approved)
        self.assertEqual(self.override_request.status, "approved")
    
    def test_rejection_process(self):
        """Test rejection process."""
        self.override_request.save()
        
        success = self.override_request.reject(
            "approver1@example.com",
            "Insufficient business justification"
        )
        
        self.assertTrue(success)
        self.assertEqual(self.override_request.status, "rejected")
        self.assertIn("Insufficient", self.override_request.rejection_reason)


@pytest.mark.django_db
class TestDocumentAPI:
    """Test Document API endpoints."""
    
    def test_document_list_requires_authentication(self, api_client, test_tenant):
        """Test document list endpoint requires authentication."""
        api_client.defaults['HTTP_HOST'] = f"{test_tenant.schema_name}.localhost"
        
        response = api_client.get('/api/documents/')
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]
    
    def test_document_list_authenticated(self, authenticated_client, test_tenant):
        """Test authenticated access to document list."""
        authenticated_client.defaults['HTTP_HOST'] = f"{test_tenant.schema_name}.localhost"
        
        response = authenticated_client.get('/api/documents/')
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)


@pytest.mark.django_db  
class TestBillingAPI:
    """Test Billing API endpoints."""
    
    def test_plans_list_public(self, api_client, test_tenant):
        """Test plans list is accessible."""
        api_client.defaults['HTTP_HOST'] = f"{test_tenant.schema_name}.localhost"

        response = api_client.get('/api/plans/')
        # May require authentication depending on implementation
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]
    
    def test_current_subscription_requires_auth(self, api_client, test_tenant):
        """Test current subscription endpoint requires authentication."""
        api_client.defaults['HTTP_HOST'] = f"{test_tenant.schema_name}.localhost"
        
        response = api_client.get('/api/billing/current_subscription/')
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_current_subscription_exposes_entitlements(self, api_client, test_tenant):
        """Test current subscription exposes module entitlement state for the UI."""
        with schema_context("public"):
            plan = Plan.objects.create(
                name="Basic",
                slug="basic",
                price_monthly=49,
                included_modules=["frameworks", "risk"],
            )
            Subscription.objects.create(
                tenant=test_tenant,
                plan=plan,
                status="active",
                enabled_modules=["frameworks", "risk"],
            )
        with tenant_context(test_tenant):
            user = User.objects.create_user(
                username="billing-user",
                email="billing-user@example.com",
                password="testpass123",
            )
        api_client.defaults['HTTP_HOST'] = f"{test_tenant.schema_name}.localhost"
        api_client.force_authenticate(user=user)

        response = api_client.get('/api/billing/current_subscription/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data["enabled_module_keys"] == ["frameworks", "risk"]
        assert any(
            module["key"] == "risk" and module["enabled"]
            for module in response.data["module_catalog"]
        )

    def test_single_module_trial_blocks_direct_api_bypass(self, test_tenant):
        """Test trial tenants cannot reach APIs outside the selected module."""
        with schema_context("public"):
            plan = Plan.objects.create(
                name="Free",
                slug="free",
                price_monthly=0,
                included_modules=["frameworks"],
            )
            Subscription.objects.create(
                tenant=test_tenant,
                plan=plan,
                status="trialing",
                enabled_modules=["assets"],
                trial_module="assets",
                trial_start=timezone.now(),
                trial_end=timezone.now() + timedelta(days=30),
            )
        with tenant_context(test_tenant):
            user = User.objects.create_user(
                username="trial-user",
                email="trial-user@example.com",
                password="testpass123",
            )

        client = APIClient()
        client.defaults['HTTP_HOST'] = f"{test_tenant.schema_name}.localhost"
        client.force_authenticate(user=user)

        allowed_response = client.get('/api/assets/assets/')
        blocked_response = client.get('/api/risk/risks/')

        assert allowed_response.status_code == status.HTTP_200_OK
        assert blocked_response.status_code == status.HTTP_403_FORBIDDEN
        assert blocked_response.json()["code"] == "module_not_enabled"
        assert blocked_response.json()["module"] == "risk"

    def test_start_trial_creates_single_module_trial(self, api_client, test_tenant):
        """Test tenants can start a one-month trial for one selected module."""
        with schema_context("public"):
            Plan.objects.create(
                name="Free",
                slug="free",
                price_monthly=0,
                included_modules=["frameworks"],
            )
        with tenant_context(test_tenant):
            user = User.objects.create_user(
                username="trial-starter",
                email="trial-starter@example.com",
                password="testpass123",
            )
        api_client.defaults['HTTP_HOST'] = f"{test_tenant.schema_name}.localhost"
        api_client.force_authenticate(user=user)

        response = api_client.post(
            '/api/billing/start_trial/',
            {'module': 'vendors'},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "trialing"
        assert response.data["trial_module"] == "vendors"
        assert response.data["enabled_module_keys"] == ["vendors"]


# Integration tests
@pytest.mark.integration
@pytest.mark.django_db
class TestFullWorkflow:
    """Test complete workflows end-to-end."""
    
    def test_tenant_subscription_limit_workflow(self, test_tenant, free_plan, test_user):
        """Test complete tenant, subscription, and limit override workflow."""
        with schema_context("public"):
            subscription = Subscription.objects.create(
                tenant=test_tenant,
                plan=free_plan,
                status="active"
            )

            assert subscription.get_effective_user_limit() == 3

            override_request = LimitOverrideRequest.objects.create(
                subscription=subscription,
                limit_type="max_users",
                current_limit=3,
                requested_limit=10,
                business_justification="Growing team needs more access",
                requested_by="test@example.com"
            )

            override_request.approve_first("approver1@example.com")
            override_request.approve_second("approver2@example.com")
            override_request.apply_override("admin@example.com")

            subscription.refresh_from_db()
            assert subscription.get_effective_user_limit() == 10
            assert override_request.status == "applied"
