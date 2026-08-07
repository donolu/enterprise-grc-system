import pytest
from django_tenants.utils import schema_context, tenant_context

from core.models import AuditEvent


@pytest.mark.django_db
def test_tenant_admin_can_read_and_update_email_settings(tenant_client, test_tenant, admin_user):
    tenant_client.force_authenticate(user=admin_user)

    response = tenant_client.get("/api/tenant-email-settings/")
    assert response.status_code == 200
    assert response.json()["sender_email_verified"] is False

    response = tenant_client.patch(
        "/api/tenant-email-settings/",
        {
            "email_sender_name": "Test Company",
            "email_sender_address": "notifications@example.com",
            "email_reply_to": "support@example.com",
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["email_sender_address"] == "notifications@example.com"
    with schema_context("public"):
        test_tenant.refresh_from_db()
        assert test_tenant.email_sender_name == "Test Company"
    with tenant_context(test_tenant):
        event = AuditEvent.objects.get(event="TENANT_EMAIL_SETTINGS_UPDATED")
        assert event.details["new"]["email_sender_address"] == "notifications@example.com"


@pytest.mark.django_db
def test_tenant_member_cannot_update_email_settings(tenant_client, test_user):
    tenant_client.force_authenticate(user=test_user)

    response = tenant_client.patch(
        "/api/tenant-email-settings/",
        {"email_sender_name": "Not authorised"},
        format="json",
    )

    assert response.status_code == 403
