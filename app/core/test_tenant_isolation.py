"""Tenant isolation regression tests."""

import pytest
from uuid import uuid4
from django.contrib.auth import get_user_model
from django.utils import timezone
from django_tenants.utils import schema_context, tenant_context
from rest_framework import status
from rest_framework.test import APIClient

from assets.models import Asset
from catalogs.models import Framework
from core.models import AuditEvent, Domain, Tenant
from core.storage import TenantAwareBlobStorage
from exports.models import AssessmentReport, TenantDataExport
from policies.models import Policy, PolicyCategory
from risk.models import Risk
from training.models import TrainingCategory, TrainingVideo

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

    def test_policy_list_and_detail_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        self._create_policy(tenant_a, "POL-A-001", "Tenant A policy", user_a)
        tenant_b_private_policy = self._create_policy(
            tenant_b,
            "POL-B-001",
            "Tenant B private policy",
            user_b,
        )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/policies/policies/")
        detail_response = client.get(
            f"/api/policies/policies/{tenant_b_private_policy.pk}/"
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_titles(list_response.json()) == ["Tenant A policy"]
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND

    def test_export_report_list_and_detail_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        self._create_assessment_report(tenant_a, "Tenant A report", user_a)

        with tenant_context(tenant_b):
            self._create_assessment_report(
                tenant_b,
                "Tenant B first report",
                user_b,
            )
            tenant_b_private_report = self._create_assessment_report(
                tenant_b,
                "Tenant B private report",
                user_b,
            )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/exports/assessment-reports/")
        detail_response = client.get(
            f"/api/exports/assessment-reports/{tenant_b_private_report.pk}/"
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_titles(list_response.json()) == ["Tenant A report"]
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND

    def test_tenant_data_export_list_and_detail_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        self._create_tenant_data_export(tenant_a, "Tenant A data export", user_a)

        with tenant_context(tenant_b):
            self._create_tenant_data_export(
                tenant_b,
                "Tenant B first data export",
                user_b,
            )
            tenant_b_private_export = self._create_tenant_data_export(
                tenant_b,
                "Tenant B private data export",
                user_b,
            )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/exports/tenant-data-exports/")
        detail_response = client.get(
            f"/api/exports/tenant-data-exports/{tenant_b_private_export.pk}/"
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_titles(list_response.json()) == ["Tenant A data export"]
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND

    def test_catalog_framework_list_and_detail_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        self._create_framework(tenant_a, "Tenant A framework", "TAF", user_a)
        with tenant_context(tenant_b):
            self._create_framework(tenant_b, "Tenant B first framework", "TBF1", user_b)
            tenant_b_private_framework = self._create_framework(
                tenant_b,
                "Tenant B private framework",
                "TBF2",
                user_b,
            )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/catalogs/api/frameworks/")
        detail_response = client.get(
            f"/api/catalogs/api/frameworks/{tenant_b_private_framework.pk}/"
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_names(list_response.json()) == ["Tenant A framework"]
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND

    def test_training_video_list_and_detail_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        self._create_training_video(tenant_a, "Tenant A video", user_a)
        tenant_b_private_video = self._create_training_video(
            tenant_b,
            "Tenant B private video",
            user_b,
        )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/training/videos/")
        detail_response = client.get(
            f"/api/training/videos/{tenant_b_private_video.pk}/"
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_titles(list_response.json()) == ["Tenant A video"]
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND

    def test_asset_list_and_detail_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        self._create_asset(tenant_a, "ASSET-A-001", "Tenant A asset", user_a)
        with tenant_context(tenant_b):
            self._create_asset(tenant_b, "ASSET-B-001", "Tenant B first asset", user_b)
            tenant_b_private_asset = self._create_asset(
                tenant_b,
                "ASSET-B-002",
                "Tenant B private asset",
                user_b,
            )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/assets/assets/")
        detail_response = client.get(f"/api/assets/assets/{tenant_b_private_asset.pk}/")

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_names(list_response.json()) == ["Tenant A asset"]
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND

    def test_audit_event_list_is_staff_only_and_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(
            tenant_a,
            "alice",
            "alice@example.com",
            is_staff=True,
        )
        user_b = self._create_user(
            tenant_b,
            "bob",
            "bob@example.com",
            is_staff=True,
        )
        with tenant_context(tenant_a):
            AuditEvent.objects.create(
                user=user_a,
                event="DOCUMENT_UPLOADED",
                details={"object": {"display": "Tenant A document"}},
            )
            AuditEvent.objects.create(
                user=user_a,
                event="TENANT_DATA_EXPORT_REQUESTED",
                details={"object": {"display": "Tenant A export"}},
            )
        with tenant_context(tenant_b):
            AuditEvent.objects.create(
                user=user_b,
                event="DOCUMENT_UPLOADED",
                details={"object": {"display": "Tenant B document"}},
            )

        client = self._authenticated_client(tenant_a, user_a)

        response = client.get("/api/audit-events/")

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        results = payload.get("results", payload) if isinstance(payload, dict) else payload
        assert {item["event"] for item in results} == {
            "DOCUMENT_UPLOADED",
            "TENANT_DATA_EXPORT_REQUESTED",
        }
        assert {item["user_email"] for item in results} == {"alice@example.com"}

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

    def _create_user(self, tenant, username, email, is_staff=False):
        with tenant_context(tenant):
            return User.objects.create_user(
                username=username,
                email=email,
                password="testpass123",
                is_staff=is_staff,
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

    def _create_policy(self, tenant, policy_code, title, user):
        with tenant_context(tenant):
            category = PolicyCategory.objects.create(
                name=f"{title} category",
                description=f"{title} category description",
            )
            return Policy.objects.create(
                policy_code=policy_code,
                title=title,
                category=category,
                owner=user,
                created_by=user,
            )

    def _create_assessment_report(self, tenant, title, user):
        with tenant_context(tenant):
            return AssessmentReport.objects.create(
                report_type="assessment_summary",
                title=title,
                requested_by=user,
            )

    def _create_tenant_data_export(self, tenant, title, user):
        with tenant_context(tenant):
            return TenantDataExport.objects.create(
                title=title,
                export_format="xlsx",
                selected_modules=["all"],
                requested_by=user,
            )

    def _create_framework(self, tenant, name, short_name, user):
        with tenant_context(tenant):
            return Framework.objects.create(
                name=name,
                short_name=short_name,
                description=f"{name} description",
                issuing_organization="Axim Cyber",
                effective_date=timezone.now().date(),
                status="active",
                created_by=user,
            )

    def _create_training_video(self, tenant, title, user):
        with tenant_context(tenant):
            category = TrainingCategory.objects.create(
                name=f"{title} category",
                description=f"{title} category description",
            )
            return TrainingVideo.objects.create(
                title=title,
                description=f"{title} description",
                category=category,
                video_provider="custom",
                video_url="https://example.com/training.mp4",
                is_published=True,
                created_by=user,
            )

    def _create_asset(self, tenant, asset_id, name, user):
        with tenant_context(tenant):
            return Asset.objects.create(
                asset_id=asset_id,
                name=name,
                asset_type="server",
                owner=user,
                created_by=user,
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

    def _response_names(self, payload):
        results = payload.get("results", payload) if isinstance(payload, dict) else payload
        return [item["name"] for item in results]
