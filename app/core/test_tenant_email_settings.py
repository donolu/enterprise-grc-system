import pytest
from django.utils import timezone
from django_tenants.utils import schema_context, tenant_context
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

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


@pytest.mark.django_db
def test_changing_sender_address_clears_verification(tenant_client, test_tenant, admin_user):
    tenant_client.force_authenticate(user=admin_user)
    with schema_context("public"):
        test_tenant.email_sender_address = "old@example.com"
        test_tenant.email_sender_verified_at = timezone.now()
        test_tenant.save(update_fields=["email_sender_address", "email_sender_verified_at"])

    response = tenant_client.patch(
        "/api/tenant-email-settings/",
        {"email_sender_address": "new@example.com"},
        format="json",
    )

    assert response.status_code == 200
    with schema_context("public"):
        test_tenant.refresh_from_db()
        assert test_tenant.email_sender_verified_at is None


@pytest.mark.django_db
def test_tenant_admin_can_request_and_confirm_sender_verification(
    tenant_client, test_tenant, admin_user
):
    tenant_client.force_authenticate(user=admin_user)
    tenant_client.patch(
        "/api/tenant-email-settings/",
        {"email_sender_address": "notifications@example.com"},
        format="json",
    )

    with patch("core.email_verification.send_mail") as send_mail:
        response = tenant_client.post("/api/tenant-email-settings/verification/")

    assert response.status_code == 202
    send_mail.assert_called_once()
    message = send_mail.call_args.args[1]
    verification_url = next(line for line in message.splitlines() if "?token=" in line)
    token = parse_qs(urlparse(verification_url).query)["token"][0]

    response = tenant_client.post(
        "/api/tenant-email-settings/verification/confirm/",
        {"token": token},
        format="json",
    )

    assert response.status_code == 200
    with schema_context("public"):
        test_tenant.refresh_from_db()
        assert test_tenant.email_sender_verified_at is not None
        assert test_tenant.email_sender_verification_token_hash == ""
        assert test_tenant.email_sender_verification_expires_at is None
    with tenant_context(test_tenant):
        assert AuditEvent.objects.filter(event="TENANT_EMAIL_VERIFIED").exists()


@pytest.mark.django_db
def test_sender_verification_rejects_invalid_token(tenant_client, admin_user):
    tenant_client.force_authenticate(user=admin_user)

    response = tenant_client.post(
        "/api/tenant-email-settings/verification/confirm/",
        {"token": "invalid-token"},
        format="json",
    )

    assert response.status_code == 400
