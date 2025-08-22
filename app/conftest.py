"""
Pytest configuration and fixtures for the GRC application.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import tenant_context
from rest_framework.test import APIClient
from core.models import Tenant, Domain, Plan, Subscription

User = get_user_model()


@pytest.fixture
def api_client():
    """Provide an API client for testing."""
    return APIClient()


@pytest.fixture
def client():
    """Provide a Django test client."""
    return Client()


@pytest.fixture
def test_tenant(db):
    """Create a test tenant for testing."""
    tenant = Tenant(
        name="Test Company",
        slug="test",
        schema_name="test"
    )
    tenant.save()
    
    domain = Domain(
        domain="test.localhost",
        tenant=tenant,
        is_primary=True
    )
    domain.save()
    
    return tenant


@pytest.fixture
def test_user(test_tenant):
    """Create a test user within tenant context."""
    with tenant_context(test_tenant):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        return user


@pytest.fixture
def admin_user(test_tenant):
    """Create an admin user within tenant context."""
    with tenant_context(test_tenant):
        user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123"
        )
        return user


@pytest.fixture
def authenticated_client(api_client, test_user):
    """Provide an authenticated API client."""
    api_client.force_authenticate(user=test_user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Provide an admin-authenticated API client."""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def free_plan(db):
    """Create a free subscription plan."""
    plan = Plan.objects.create(
        name="Free",
        slug="free",
        description="Free plan for testing",
        price_monthly=0,
        max_users=3,
        max_documents=50,
        max_frameworks=1,
        has_api_access=False,
        has_advanced_reporting=False,
        has_priority_support=False
    )
    return plan


@pytest.fixture
def basic_plan(db):
    """Create a basic subscription plan."""
    plan = Plan.objects.create(
        name="Basic",
        slug="basic",
        description="Basic plan for testing",
        price_monthly=49,
        max_users=10,
        max_documents=500,
        max_frameworks=5,
        has_api_access=True,
        has_advanced_reporting=False,
        has_priority_support=False
    )
    return plan


@pytest.fixture
def test_subscription(test_tenant, free_plan):
    """Create a test subscription."""
    subscription = Subscription.objects.create(
        tenant=test_tenant,
        plan=free_plan,
        status="active"
    )
    return subscription


@pytest.fixture
def tenant_client(api_client, test_tenant):
    """Provide an API client with tenant context."""
    # Set tenant in the client's context
    api_client.defaults['HTTP_HOST'] = f"{test_tenant.schema_name}.localhost"
    return api_client


class TenantAPITestCase(TenantTestCase):
    """Base test case for tenant-aware API testing."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = cls.tenant
        
    def setUp(self):
        super().setUp()
        self.api_client = APIClient()
        # Ensure we're in the right tenant context
        self.api_client.defaults['HTTP_HOST'] = f"{self.tenant.schema_name}.localhost"