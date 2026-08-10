import pytest
from django.utils import timezone
from django_tenants.utils import schema_context

from core.models import AuditEvent


@pytest.mark.django_db
def test_tenant_admin_can_read_and_update_tax_profile(tenant_client, test_tenant, admin_user):
    tenant_client.force_authenticate(user=admin_user)

    response = tenant_client.get("/api/tenant-tax-profile/")

    assert response.status_code == 200
    assert response.json()["tax_identifier_status"] == "unknown"

    response = tenant_client.patch(
        "/api/tenant-tax-profile/",
        {
            "billing_country": "gb",
            "business_type": "business",
            "tax_identifier": "GB123456789",
            "tax_identifier_type": "vat",
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["billing_country"] == "GB"
    assert response.json()["tax_identifier_status"] == "unknown"
    with schema_context("public"):
        test_tenant.refresh_from_db()
        assert test_tenant.billing_country == "GB"
        assert test_tenant.tax_identifier == "GB123456789"
    event = AuditEvent.objects.get(event="TENANT_TAX_PROFILE_UPDATED")
    assert event.details["new"]["tax_identifier"] == {"configured": True}
    assert "GB123456789" not in str(event.details)


@pytest.mark.django_db
def test_tenant_member_cannot_update_tax_profile(tenant_client, test_user):
    tenant_client.force_authenticate(user=test_user)

    response = tenant_client.patch(
        "/api/tenant-tax-profile/",
        {"billing_country": "GB"},
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_tax_profile_changes_reset_validation_state(tenant_client, test_tenant, admin_user):
    tenant_client.force_authenticate(user=admin_user)
    with schema_context("public"):
        test_tenant.tax_identifier = "GB123456789"
        test_tenant.tax_identifier_type = "vat"
        test_tenant.tax_identifier_status = "valid"
        test_tenant.tax_identifier_validated_at = timezone.now()
        test_tenant.save(
            update_fields=[
                "tax_identifier",
                "tax_identifier_type",
                "tax_identifier_status",
                "tax_identifier_validated_at",
            ]
        )

    response = tenant_client.patch(
        "/api/tenant-tax-profile/",
        {"tax_identifier": "GB987654321"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["tax_identifier_status"] == "unknown"
    assert response.json()["tax_identifier_validated_at"] is None


@pytest.mark.django_db
def test_tax_profile_does_not_accept_client_validation_state(tenant_client, admin_user):
    tenant_client.force_authenticate(user=admin_user)

    response = tenant_client.patch(
        "/api/tenant-tax-profile/",
        {"tax_identifier_status": "valid"},
        format="json",
    )

    assert response.status_code == 400
