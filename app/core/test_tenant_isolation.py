"""Tenant isolation regression tests."""

import pytest
from uuid import uuid4
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context, tenant_context
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Domain, Tenant
from core.storage import TenantAwareBlobStorage
from risk.models import Risk

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestTenantIsolation:
    """Verify tenant schema boundaries for representative tenant-owned data."""

    def test_risk_list_is_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        self._create_risk(tenant_a, "SHARED-RISK-ID", "Tenant A risk", user_a)
        self._create_risk(tenant_b, "SHARED-RISK-ID", "Tenant B risk", user_b)

        client = self._authenticated_client(tenant_a, user_a)

        response = client.get("/api/risk/risks/")

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert self._response_count(payload) == 1
        assert self._response_titles(payload) == ["Tenant A risk"]

    def test_risk_detail_cannot_cross_tenant_boundary_by_pk(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        self._create_risk(tenant_a, "RISK-A-001", "Tenant A risk", user_a)

        with tenant_context(tenant_b):
            self._create_risk(tenant_b, "RISK-B-001", "Tenant B first risk", user_b)
            tenant_b_private_risk = self._create_risk(
                tenant_b,
                "RISK-B-002",
                "Tenant B private risk",
                user_b,
            )

        client = self._authenticated_client(tenant_a, user_a)

        response = client.get(f"/api/risk/risks/{tenant_b_private_risk.pk}/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_storage_container_name_uses_current_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")
        storage = TenantAwareBlobStorage(connection_string="UseDevelopmentStorage=true")

        with tenant_context(tenant_a):
            container_a = storage._get_tenant_container_name()

        with tenant_context(tenant_b):
            container_b = storage._get_tenant_container_name()

        assert container_a == f"tenant-{tenant_a.slug}"
        assert container_b == f"tenant-{tenant_b.slug}"
        assert container_a != container_b

    def _create_tenant(self, schema_name, slug, name):
        suffix = uuid4().hex[:8]
        schema_name = f"{schema_name}_{suffix}"
        slug = f"{slug}-{suffix}"
        with schema_context("public"):
            tenant = Tenant.objects.create(
                name=name,
                slug=slug,
                schema_name=schema_name,
            )
            Domain.objects.create(
                tenant=tenant,
                domain=f"{slug}.localhost",
                is_primary=True,
            )
        return tenant

    def _create_user(self, tenant, username, email):
        with tenant_context(tenant):
            return User.objects.create_user(
                username=username,
                email=email,
                password="testpass123",
            )

    def _create_risk(self, tenant, risk_id, title, user):
        with tenant_context(tenant):
            return Risk.objects.create(
                risk_id=risk_id,
                title=title,
                description=f"{title} description",
                impact=3,
                likelihood=3,
                created_by=user,
                risk_owner=user,
            )

    def _authenticated_client(self, tenant, user):
        client = APIClient()
        client.defaults["HTTP_HOST"] = f"{tenant.slug}.localhost"
        client.force_authenticate(user=user)
        return client

    def _response_count(self, payload):
        if isinstance(payload, dict) and "count" in payload:
            return payload["count"]
        return len(payload)

    def _response_titles(self, payload):
        results = payload.get("results", payload) if isinstance(payload, dict) else payload
        return [item["title"] for item in results]
