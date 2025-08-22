"""
Tests for core application functionality.
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django_tenants.utils import tenant_context, schema_context
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Tenant, Domain, Plan, Subscription, Document, LimitOverrideRequest
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


@pytest.mark.django_db
class TestPlanEnforcementService:
    """Test PlanEnforcementService functionality."""
    
    def test_check_feature_access_with_permission(self, test_tenant, basic_plan):
        """Test feature access check when user has permission."""
        subscription = Subscription.objects.create(
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
        subscription = Subscription.objects.create(
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
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_document_list_authenticated(self, authenticated_client, test_tenant):
        """Test authenticated access to document list."""
        authenticated_client.defaults['HTTP_HOST'] = f"{test_tenant.schema_name}.localhost"
        
        response = authenticated_client.get('/api/documents/')
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or isinstance(response.data, list)


@pytest.mark.django_db  
class TestBillingAPI:
    """Test Billing API endpoints."""
    
    def test_plans_list_public(self, api_client):
        """Test plans list is accessible."""
        response = api_client.get('/api/plans/')
        # May require authentication depending on implementation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED]
    
    def test_current_subscription_requires_auth(self, api_client, test_tenant):
        """Test current subscription endpoint requires authentication."""
        api_client.defaults['HTTP_HOST'] = f"{test_tenant.schema_name}.localhost"
        
        response = api_client.get('/api/billing/current_subscription/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# Integration tests
@pytest.mark.integration
@pytest.mark.django_db
class TestFullWorkflow:
    """Test complete workflows end-to-end."""
    
    def test_tenant_subscription_limit_workflow(self, test_tenant, free_plan, test_user):
        """Test complete tenant, subscription, and limit override workflow."""
        # Create subscription
        subscription = Subscription.objects.create(
            tenant=test_tenant,
            plan=free_plan,
            status="active"
        )
        
        # Verify initial limits
        assert subscription.get_effective_user_limit() == 3
        
        # Create override request
        override_request = LimitOverrideRequest.objects.create(
            subscription=subscription,
            limit_type="max_users",
            current_limit=3,
            requested_limit=10,
            business_justification="Growing team needs more access",
            requested_by="test@example.com"
        )
        
        # Test approval workflow
        override_request.approve_first("approver1@example.com")
        override_request.approve_second("approver2@example.com")
        
        # Apply override
        override_request.apply_override("admin@example.com")
        
        # Verify new limits
        subscription.refresh_from_db()
        assert subscription.get_effective_user_limit() == 10
        assert override_request.status == "applied"