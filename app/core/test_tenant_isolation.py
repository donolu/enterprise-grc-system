"""Tenant isolation regression tests."""

import pytest
from datetime import timedelta
from uuid import uuid4
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import Resolver404, resolve
from django.utils import timezone
from django_tenants.utils import schema_context, tenant_context
from rest_framework import status
from rest_framework.test import APIClient

from assets.models import Asset
from calendarhub.models import CalendarEvent
from catalogs.models import Framework
from compliance.models import GovernanceArtefact
from core.models import AuditEvent, Document, Domain, Tenant
from core.storage import TenantAwareBlobStorage
from exports.models import AssessmentReport, TenantDataExport
from knowledge.models import KnowledgeArticle, KnowledgeCategory
from policies.models import Policy, PolicyAcknowledgment, PolicyCategory, PolicyDistribution, PolicyVersion
from risk.models import Risk, RiskAction, RiskActionReminderConfiguration, RiskCategory, RiskMatrix
from training.models import TrainingCategory, TrainingVideo
from vendors.models import (
    Vendor,
    VendorCategory,
    VendorContact,
    VendorNote,
    VendorService,
    VendorTask,
)
from vuln.models import ScanTarget

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

    def test_risk_category_list_and_detail_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        self._create_user(tenant_b, "bob", "bob@example.com")
        self._create_risk_category(tenant_a, "Tenant A risk category")
        with tenant_context(tenant_b):
            self._create_risk_category(tenant_b, "Tenant B first risk category")
            tenant_b_private_category = self._create_risk_category(
                tenant_b,
                "Tenant B private risk category",
            )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/risk/categories/")
        detail_response = client.get(
            f"/api/risk/categories/{tenant_b_private_category.pk}/"
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_names(list_response.json()) == ["Tenant A risk category"]
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND

    def test_risk_matrix_list_and_detail_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        self._create_risk_matrix(tenant_a, "Tenant A risk matrix", user_a)
        with tenant_context(tenant_b):
            self._create_risk_matrix(tenant_b, "Tenant B first risk matrix", user_b)
            tenant_b_private_matrix = self._create_risk_matrix(
                tenant_b,
                "Tenant B private risk matrix",
                user_b,
            )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/risk/matrices/")
        detail_response = client.get(
            f"/api/risk/matrices/{tenant_b_private_matrix.pk}/"
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_names(list_response.json()) == ["Tenant A risk matrix"]
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND

    def test_risk_action_list_and_detail_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        risk_a = self._create_risk(tenant_a, "RISK-A-001", "Tenant A risk", user_a)
        self._create_risk_action(tenant_a, risk_a, "Tenant A risk action", user_a)
        with tenant_context(tenant_b):
            risk_b = self._create_risk(tenant_b, "RISK-B-001", "Tenant B risk", user_b)
            self._create_risk_action(
                tenant_b,
                risk_b,
                "Tenant B first risk action",
                user_b,
            )
            tenant_b_private_action = self._create_risk_action(
                tenant_b,
                risk_b,
                "Tenant B private risk action",
                user_b,
            )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/risk/actions/")
        detail_response = client.get(
            f"/api/risk/actions/{tenant_b_private_action.pk}/"
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_titles(list_response.json()) == ["Tenant A risk action"]
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND

    def test_risk_reminder_config_list_and_detail_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        user_b_alt = self._create_user(tenant_b, "brian", "brian@example.com")
        self._create_risk_reminder_config(tenant_a, user_a)
        with tenant_context(tenant_b):
            self._create_risk_reminder_config(tenant_b, user_b)
            tenant_b_private_config = self._create_risk_reminder_config(
                tenant_b,
                user_b_alt,
            )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/risk/reminder-config/")
        detail_response = client.get(
            f"/api/risk/reminder-config/{tenant_b_private_config.pk}/"
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_field(list_response.json(), "user") == [user_a.pk]
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND

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

    def test_policy_category_list_and_detail_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        self._create_user(tenant_b, "bob", "bob@example.com")
        self._create_policy_category(tenant_a, "Tenant A policy category")
        with tenant_context(tenant_b):
            self._create_policy_category(tenant_b, "Tenant B first policy category")
            tenant_b_private_category = self._create_policy_category(
                tenant_b,
                "Tenant B private policy category",
            )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/policies/categories/")
        detail_response = client.get(
            f"/api/policies/categories/{tenant_b_private_category.pk}/"
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_names(list_response.json()) == [
            "Tenant A policy category"
        ]
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND

    def test_policy_version_list_and_detail_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        policy_a = self._create_policy(tenant_a, "POL-A-001", "Tenant A policy", user_a)
        self._create_policy_version(tenant_a, policy_a, "1.0", user_a)
        with tenant_context(tenant_b):
            policy_b = self._create_policy(
                tenant_b,
                "POL-B-001",
                "Tenant B policy",
                user_b,
            )
            self._create_policy_version(tenant_b, policy_b, "1.0", user_b)
            tenant_b_private_version = self._create_policy_version(
                tenant_b,
                policy_b,
                "2.0",
                user_b,
            )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/policies/versions/")
        detail_response = client.get(
            f"/api/policies/versions/{tenant_b_private_version.pk}/"
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_field(list_response.json(), "version_number") == ["1.0"]
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND

    def test_policy_acknowledgment_list_and_detail_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        policy_a = self._create_policy(tenant_a, "POL-A-001", "Tenant A policy", user_a)
        version_a = self._create_policy_version(tenant_a, policy_a, "1.0", user_a)
        self._create_policy_acknowledgment(tenant_a, version_a, user_a)
        with tenant_context(tenant_b):
            policy_b = self._create_policy(
                tenant_b,
                "POL-B-001",
                "Tenant B policy",
                user_b,
            )
            version_b = self._create_policy_version(tenant_b, policy_b, "1.0", user_b)
            tenant_b_private_acknowledgment = self._create_policy_acknowledgment(
                tenant_b,
                version_b,
                user_b,
            )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/policies/acknowledgments/")
        detail_response = client.get(
            f"/api/policies/acknowledgments/{tenant_b_private_acknowledgment.pk}/"
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_field(list_response.json(), "policy_title") == [
            "Tenant A policy"
        ]
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND

    def test_policy_distribution_list_and_detail_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        policy_a = self._create_policy(tenant_a, "POL-A-001", "Tenant A policy", user_a)
        version_a = self._create_policy_version(tenant_a, policy_a, "1.0", user_a)
        self._create_policy_distribution(tenant_a, version_a, user_a, user_a)
        with tenant_context(tenant_b):
            policy_b = self._create_policy(
                tenant_b,
                "POL-B-001",
                "Tenant B policy",
                user_b,
            )
            version_b = self._create_policy_version(tenant_b, policy_b, "1.0", user_b)
            tenant_b_private_distribution = self._create_policy_distribution(
                tenant_b,
                version_b,
                user_b,
                user_b,
            )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/policies/distributions/")
        detail_response = client.get(
            f"/api/policies/distributions/{tenant_b_private_distribution.pk}/"
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_field(list_response.json(), "policy_title") == [
            "Tenant A policy"
        ]
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

    def test_document_list_detail_and_download_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        self._create_document(tenant_a, "Tenant A document", user_a)

        with tenant_context(tenant_b):
            self._create_document(tenant_b, "Tenant B first document", user_b)
            tenant_b_private_document = self._create_document(
                tenant_b,
                "Tenant B private document",
                user_b,
            )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/documents/")
        detail_response = client.get(f"/api/documents/{tenant_b_private_document.pk}/")
        download_response = client.get(
            f"/api/documents/{tenant_b_private_document.pk}/download/"
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_titles(list_response.json()) == ["Tenant A document"]
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND
        assert download_response.status_code == status.HTTP_404_NOT_FOUND

    def test_assessment_report_actions_do_not_expose_cross_tenant_generated_files(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        report_a = self._create_assessment_report(tenant_a, "Tenant A report", user_a)
        document_a = self._create_document(tenant_a, "Tenant A report file", user_a)
        self._complete_assessment_report(tenant_a, report_a, document_a)

        with tenant_context(tenant_b):
            self._create_assessment_report(
                tenant_b,
                "Tenant B first report",
                user_b,
            )
            document_b = self._create_document(
                tenant_b,
                "Tenant B private report file",
                user_b,
            )
            tenant_b_private_report = self._create_assessment_report(
                tenant_b,
                "Tenant B private report",
                user_b,
            )
            self._complete_assessment_report(
                tenant_b,
                tenant_b_private_report,
                document_b,
            )

        client = self._authenticated_client(tenant_a, user_a)

        status_response = client.get(
            f"/api/exports/assessment-reports/{report_a.pk}/status_check/"
        )
        download_response = client.get(
            f"/api/exports/assessment-reports/{report_a.pk}/download/"
        )
        cross_status_response = client.get(
            f"/api/exports/assessment-reports/{tenant_b_private_report.pk}/status_check/"
        )
        cross_download_response = client.get(
            f"/api/exports/assessment-reports/{tenant_b_private_report.pk}/download/"
        )

        assert status_response.status_code == status.HTTP_200_OK
        assert f"/api/documents/{document_a.pk}/download/" in status_response.json()[
            "download_url"
        ]
        assert download_response.status_code == status.HTTP_200_OK
        assert download_response.json()["download_url"].endswith(
            f"/api/documents/{document_a.pk}/download/"
        )
        assert cross_status_response.status_code == status.HTTP_404_NOT_FOUND
        assert cross_download_response.status_code == status.HTTP_404_NOT_FOUND

    def test_tenant_data_export_actions_do_not_expose_cross_tenant_generated_files(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        export_a = self._create_tenant_data_export(
            tenant_a,
            "Tenant A data export",
            user_a,
        )
        document_a = self._create_document(tenant_a, "Tenant A export file", user_a)
        self._complete_tenant_data_export(tenant_a, export_a, document_a)

        with tenant_context(tenant_b):
            self._create_tenant_data_export(
                tenant_b,
                "Tenant B first data export",
                user_b,
            )
            document_b = self._create_document(
                tenant_b,
                "Tenant B private export file",
                user_b,
            )
            tenant_b_private_export = self._create_tenant_data_export(
                tenant_b,
                "Tenant B private data export",
                user_b,
            )
            self._complete_tenant_data_export(
                tenant_b,
                tenant_b_private_export,
                document_b,
            )

        client = self._authenticated_client(tenant_a, user_a)

        status_response = client.get(
            f"/api/exports/tenant-data-exports/{export_a.pk}/status_check/"
        )
        download_response = client.get(
            f"/api/exports/tenant-data-exports/{export_a.pk}/download/"
        )
        cross_status_response = client.get(
            f"/api/exports/tenant-data-exports/{tenant_b_private_export.pk}/status_check/"
        )
        cross_download_response = client.get(
            f"/api/exports/tenant-data-exports/{tenant_b_private_export.pk}/download/"
        )

        assert status_response.status_code == status.HTTP_200_OK
        assert f"/api/documents/{document_a.pk}/download/" in status_response.json()[
            "download_url"
        ]
        assert download_response.status_code == status.HTTP_200_OK
        assert download_response.json()["document_id"] == document_a.pk
        assert download_response.json()["download_url"].endswith(
            f"/api/documents/{document_a.pk}/download/"
        )
        assert cross_status_response.status_code == status.HTTP_404_NOT_FOUND
        assert cross_download_response.status_code == status.HTTP_404_NOT_FOUND

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

    def test_vendor_list_and_detail_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        self._create_vendor(tenant_a, "Tenant A vendor", user_a)
        with tenant_context(tenant_b):
            self._create_vendor(tenant_b, "Tenant B first vendor", user_b)
            tenant_b_private_vendor = self._create_vendor(
                tenant_b,
                "Tenant B private vendor",
                user_b,
            )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/vendors/vendors/")
        detail_response = client.get(
            f"/api/vendors/vendors/{tenant_b_private_vendor.pk}/"
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_names(list_response.json()) == ["Tenant A vendor"]
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND

    def test_vendor_task_list_and_detail_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        vendor_a = self._create_vendor(tenant_a, "Tenant A vendor", user_a)
        self._create_vendor_task(
            tenant_a,
            vendor_a,
            "Tenant A vendor task",
            user_a,
        )
        with tenant_context(tenant_b):
            vendor_b = self._create_vendor(tenant_b, "Tenant B vendor", user_b)
            self._create_vendor_task(
                tenant_b,
                vendor_b,
                "Tenant B first vendor task",
                user_b,
            )
            tenant_b_private_task = self._create_vendor_task(
                tenant_b,
                vendor_b,
                "Tenant B private vendor task",
                user_b,
            )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/vendors/tasks/")
        detail_response = client.get(
            f"/api/vendors/tasks/{tenant_b_private_task.pk}/"
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_titles(list_response.json()) == ["Tenant A vendor task"]
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND

    def test_vendor_category_list_and_detail_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        self._create_vendor_category(tenant_a, "Tenant A category")
        with tenant_context(tenant_b):
            self._create_vendor_category(tenant_b, "Tenant B first category")
            tenant_b_private_category = self._create_vendor_category(
                tenant_b,
                "Tenant B private category",
            )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/vendors/categories/")
        detail_response = client.get(
            f"/api/vendors/categories/{tenant_b_private_category.pk}/"
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_names(list_response.json()) == ["Tenant A category"]
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND

    def test_vendor_contact_list_and_detail_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        vendor_a = self._create_vendor(tenant_a, "Tenant A vendor", user_a)
        self._create_vendor_contact(tenant_a, vendor_a, "Tenant A")
        with tenant_context(tenant_b):
            vendor_b = self._create_vendor(tenant_b, "Tenant B vendor", user_b)
            self._create_vendor_contact(tenant_b, vendor_b, "Tenant B first")
            tenant_b_private_contact = self._create_vendor_contact(
                tenant_b,
                vendor_b,
                "Tenant B private",
            )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/vendors/contacts/")
        detail_response = client.get(
            f"/api/vendors/contacts/{tenant_b_private_contact.pk}/"
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_field(list_response.json(), "first_name") == ["Tenant A"]
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND

    def test_vendor_service_list_and_detail_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        vendor_a = self._create_vendor(tenant_a, "Tenant A vendor", user_a)
        self._create_vendor_service(tenant_a, vendor_a, "Tenant A service")
        with tenant_context(tenant_b):
            vendor_b = self._create_vendor(tenant_b, "Tenant B vendor", user_b)
            self._create_vendor_service(tenant_b, vendor_b, "Tenant B first service")
            tenant_b_private_service = self._create_vendor_service(
                tenant_b,
                vendor_b,
                "Tenant B private service",
            )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/vendors/services/")
        detail_response = client.get(
            f"/api/vendors/services/{tenant_b_private_service.pk}/"
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_names(list_response.json()) == ["Tenant A service"]
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND

    def test_vendor_note_list_and_detail_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        vendor_a = self._create_vendor(tenant_a, "Tenant A vendor", user_a)
        self._create_vendor_note(tenant_a, vendor_a, "Tenant A note", user_a)
        with tenant_context(tenant_b):
            vendor_b = self._create_vendor(tenant_b, "Tenant B vendor", user_b)
            self._create_vendor_note(tenant_b, vendor_b, "Tenant B first note", user_b)
            tenant_b_private_note = self._create_vendor_note(
                tenant_b,
                vendor_b,
                "Tenant B private note",
                user_b,
            )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/vendors/notes/")
        detail_response = client.get(
            f"/api/vendors/notes/{tenant_b_private_note.pk}/"
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_titles(list_response.json()) == ["Tenant A note"]
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND

    def test_compliance_artefact_list_and_detail_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        self._create_governance_artefact(tenant_a, "Tenant A artefact", user_a)
        with tenant_context(tenant_b):
            self._create_governance_artefact(tenant_b, "Tenant B first artefact", user_b)
            tenant_b_private_artefact = self._create_governance_artefact(
                tenant_b,
                "Tenant B private artefact",
                user_b,
            )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/compliance/artefacts/")
        detail_response = client.get(
            f"/api/compliance/artefacts/{tenant_b_private_artefact.pk}/"
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_titles(list_response.json()) == ["Tenant A artefact"]
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND

    def test_knowledge_article_list_and_detail_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        self._create_knowledge_article(tenant_a, "Tenant A article", user_a)
        with tenant_context(tenant_b):
            self._create_knowledge_article(tenant_b, "Tenant B first article", user_b)
            tenant_b_private_article = self._create_knowledge_article(
                tenant_b,
                "Tenant B private article",
                user_b,
            )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/knowledge/articles/")
        detail_response = client.get(
            f"/api/knowledge/articles/{tenant_b_private_article.pk}/"
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_titles(list_response.json()) == ["Tenant A article"]
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND

    def test_calendar_event_list_and_detail_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        self._create_calendar_event(tenant_a, "Tenant A event", user_a)
        with tenant_context(tenant_b):
            self._create_calendar_event(tenant_b, "Tenant B first event", user_b)
            tenant_b_private_event = self._create_calendar_event(
                tenant_b,
                "Tenant B private event",
                user_b,
            )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/calendar/events/")
        detail_response = client.get(
            f"/api/calendar/events/{tenant_b_private_event.pk}/"
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_titles(list_response.json()) == ["Tenant A event"]
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND

    def test_vulnerability_target_list_and_detail_are_scoped_to_request_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        user_a = self._create_user(tenant_a, "alice", "alice@example.com")
        user_b = self._create_user(tenant_b, "bob", "bob@example.com")
        self._create_scan_target(tenant_a, "Tenant A scan target", user_a)
        with tenant_context(tenant_b):
            self._create_scan_target(tenant_b, "Tenant B first scan target", user_b)
            tenant_b_private_target = self._create_scan_target(
                tenant_b,
                "Tenant B private scan target",
                user_b,
            )

        client = self._authenticated_client(tenant_a, user_a)

        list_response = client.get("/api/vuln/targets/")
        detail_response = client.get(
            f"/api/vuln/targets/{tenant_b_private_target.pk}/"
        )

        assert list_response.status_code == status.HTTP_200_OK
        assert self._response_count(list_response.json()) == 1
        assert self._response_names(list_response.json()) == ["Tenant A scan target"]
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

    def test_storage_fallback_cache_is_scoped_to_current_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")
        storage = TenantAwareBlobStorage()

        with tenant_context(tenant_a):
            location_a = storage.fallback_storage.location

        with tenant_context(tenant_b):
            location_b = storage.fallback_storage.location

        assert location_a.endswith(f"tenant-{tenant_a.slug}")
        assert location_b.endswith(f"tenant-{tenant_b.slug}")
        assert location_a != location_b

    def test_public_urlconf_does_not_mount_tenant_api_routes(self):
        with override_settings(ROOT_URLCONF="app.public_urls"):
            with pytest.raises(Resolver404):
                resolve("/api/risk/risks/")

            with pytest.raises(Resolver404):
                resolve("/api/vendors/vendors/")

    def test_session_cookie_from_one_tenant_does_not_authenticate_another_tenant(self):
        tenant_a = self._create_tenant("tenant_a", "tenant-a", "Tenant A")
        tenant_b = self._create_tenant("tenant_b", "tenant-b", "Tenant B")

        self._create_user(tenant_a, "alice", "alice@example.com")
        self._create_user(tenant_b, "bob", "bob@example.com")

        client = APIClient()
        client.defaults["HTTP_HOST"] = f"{tenant_b.slug}.localhost"
        with tenant_context(tenant_b):
            assert client.login(username="bob", password="testpass123")

        client.defaults["HTTP_HOST"] = f"{tenant_a.slug}.localhost"
        response = client.get("/api/auth/me/")

        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

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

    def _create_risk_category(self, tenant, name):
        with tenant_context(tenant):
            return RiskCategory.objects.create(
                name=name,
                description=f"{name} description",
            )

    def _create_risk_matrix(self, tenant, name, user):
        with tenant_context(tenant):
            return RiskMatrix.objects.create(
                name=name,
                description=f"{name} description",
                impact_levels=5,
                likelihood_levels=5,
                created_by=user,
            )

    def _create_risk_action(self, tenant, risk, title, user):
        with tenant_context(tenant):
            return RiskAction.objects.create(
                risk=risk,
                title=title,
                description=f"{title} description",
                action_type="corrective",
                due_date=timezone.now().date() + timedelta(days=14),
                assigned_to=user,
                created_by=user,
            )

    def _create_risk_reminder_config(self, tenant, user):
        with tenant_context(tenant):
            return RiskActionReminderConfiguration.objects.create(
                user=user,
                advance_warning_days=7,
                reminder_frequency="daily",
            )

    def _create_policy(self, tenant, policy_code, title, user):
        with tenant_context(tenant):
            category = self._create_policy_category(tenant, f"{title} category")
            return Policy.objects.create(
                policy_code=policy_code,
                title=title,
                category=category,
                owner=user,
                created_by=user,
            )

    def _create_policy_category(self, tenant, name):
        with tenant_context(tenant):
            return PolicyCategory.objects.create(
                name=name,
                description=f"{name} description",
            )

    def _create_policy_version(self, tenant, policy, version_number, user):
        document = SimpleUploadedFile(
            f"{policy.policy_code}-{version_number}.pdf",
            b"%PDF-1.4\n% tenant isolation fixture\n",
            content_type="application/pdf",
        )
        with tenant_context(tenant):
            return PolicyVersion.objects.create(
                policy=policy,
                version_number=version_number,
                document=document,
                summary=f"{policy.title} version {version_number}",
                created_by=user,
            )

    def _create_policy_acknowledgment(self, tenant, version, user):
        with tenant_context(tenant):
            return PolicyAcknowledgment.objects.create(
                policy_version=version,
                user=user,
            )

    def _create_policy_distribution(self, tenant, version, user, distributed_by):
        with tenant_context(tenant):
            return PolicyDistribution.objects.create(
                policy_version=version,
                distributed_to=user,
                distributed_by=distributed_by,
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

    def _create_document(self, tenant, title, user):
        slug = title.lower().replace(" ", "-")
        upload = SimpleUploadedFile(
            f"{slug}.pdf",
            b"%PDF-1.4\n% tenant isolation fixture\n",
            content_type="application/pdf",
        )
        with tenant_context(tenant):
            return Document.objects.create(
                title=title,
                description=f"{title} description",
                file=upload,
                uploaded_by=user,
                mime_type="application/pdf",
            )

    def _complete_assessment_report(self, tenant, report, document):
        with tenant_context(tenant):
            report.status = "completed"
            report.generated_file = document
            report.generation_completed_at = timezone.now()
            report.save(
                update_fields=[
                    "status",
                    "generated_file",
                    "generation_completed_at",
                ]
            )
            return report

    def _complete_tenant_data_export(self, tenant, data_export, document):
        with tenant_context(tenant):
            data_export.status = "completed"
            data_export.generated_file = document
            data_export.generation_completed_at = timezone.now()
            data_export.record_counts = {"documents": 1}
            data_export.save(
                update_fields=[
                    "status",
                    "generated_file",
                    "generation_completed_at",
                    "record_counts",
                ]
            )
            return data_export

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

    def _create_vendor(self, tenant, name, user):
        with tenant_context(tenant):
            category = self._create_vendor_category(tenant, f"{name} category")
            return Vendor.objects.create(
                name=name,
                category=category,
                business_description=f"{name} description",
                created_by=user,
                assigned_to=user,
            )

    def _create_vendor_category(self, tenant, name):
        with tenant_context(tenant):
            return VendorCategory.objects.create(
                name=name,
                description=f"{name} description",
            )

    def _create_vendor_task(self, tenant, vendor, title, user):
        with tenant_context(tenant):
            return VendorTask.objects.create(
                vendor=vendor,
                title=title,
                description=f"{title} description",
                task_type="security_review",
                due_date=timezone.now().date() + timedelta(days=7),
                assigned_to=user,
                created_by=user,
            )

    def _create_vendor_contact(self, tenant, vendor, first_name):
        slug = first_name.lower().replace(" ", "-")
        with tenant_context(tenant):
            return VendorContact.objects.create(
                vendor=vendor,
                first_name=first_name,
                last_name="Contact",
                email=f"{slug}@example.com",
                contact_type="primary",
            )

    def _create_vendor_service(self, tenant, vendor, name):
        with tenant_context(tenant):
            return VendorService.objects.create(
                vendor=vendor,
                name=name,
                description=f"{name} description",
                category="it_services",
                data_classification="internal",
            )

    def _create_vendor_note(self, tenant, vendor, title, user):
        with tenant_context(tenant):
            return VendorNote.objects.create(
                vendor=vendor,
                title=title,
                content=f"{title} content",
                note_type="general",
                created_by=user,
            )

    def _create_governance_artefact(self, tenant, title, user):
        with tenant_context(tenant):
            return GovernanceArtefact.objects.create(
                title=title,
                artefact_type="scope_document",
                description=f"{title} description",
                owner=user,
                created_by=user,
            )

    def _create_knowledge_article(self, tenant, title, user):
        with tenant_context(tenant):
            slug = title.lower().replace(" ", "-")
            category = KnowledgeCategory.objects.create(
                name=f"{title} category",
                slug=f"{slug}-category",
                module_key="administration",
                created_by=user,
            )
            return KnowledgeArticle.objects.create(
                title=title,
                slug=slug,
                summary=f"{title} summary",
                body=f"{title} body",
                category=category,
                module_key="administration",
                status="published",
                created_by=user,
                updated_by=user,
            )

    def _create_calendar_event(self, tenant, title, user):
        with tenant_context(tenant):
            return CalendarEvent.objects.create(
                title=title,
                description=f"{title} description",
                due_date=timezone.now().date() + timedelta(days=14),
                owner=user,
                created_by=user,
            )

    def _create_scan_target(self, tenant, name, user):
        with tenant_context(tenant):
            slug = name.lower().replace(" ", "-")
            return ScanTarget.objects.create(
                name=name,
                target_type="web",
                address=f"https://{slug}.example.com",
                status="approved",
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

    def _response_field(self, payload, field):
        results = payload.get("results", payload) if isinstance(payload, dict) else payload
        return [item[field] for item in results]
