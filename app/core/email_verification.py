import hashlib
import hmac
import secrets
from datetime import timedelta
from urllib.parse import quote

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django_tenants.utils import schema_context

from .models import Tenant


VERIFICATION_TTL = timedelta(hours=24)


class SenderVerificationError(ValueError):
    """Raised when sender verification cannot be requested or completed."""


def request_sender_verification(tenant):
    """Issue a one-time sender verification token and email its confirmation link."""
    with transaction.atomic(), schema_context("public"):
        locked_tenant = Tenant.objects.select_for_update().get(pk=tenant.pk)
        if not locked_tenant.email_sender_address:
            raise SenderVerificationError("Configure a sender email address first.")

        token = secrets.token_urlsafe(32)
        now = timezone.now()
        locked_tenant.email_sender_verification_token_hash = _hash_token(token)
        locked_tenant.email_sender_verification_expires_at = now + VERIFICATION_TTL
        locked_tenant.email_sender_verified_at = None
        locked_tenant.save(
            update_fields=[
                "email_sender_verification_token_hash",
                "email_sender_verification_expires_at",
                "email_sender_verified_at",
            ]
        )
        expires_at = locked_tenant.email_sender_verification_expires_at
        recipient = locked_tenant.email_sender_address

    verification_url = f"{settings.EMAIL_VERIFICATION_BASE_URL.rstrip('/')}?token={quote(token)}"
    try:
        send_mail(
            "Verify your Provena sender email address",
            "Confirm this sender address by opening the following link:\n\n"
            f"{verification_url}\n\nThis link expires in 24 hours.",
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=False,
        )
    except Exception:
        with transaction.atomic(), schema_context("public"):
            locked_tenant = Tenant.objects.select_for_update().get(pk=tenant.pk)
            locked_tenant.email_sender_verification_token_hash = ""
            locked_tenant.email_sender_verification_expires_at = None
            locked_tenant.save(
                update_fields=[
                    "email_sender_verification_token_hash",
                    "email_sender_verification_expires_at",
                ]
            )
        raise

    return expires_at


def confirm_sender_verification(tenant, token):
    """Consume a valid sender verification token for the current tenant."""
    if not token:
        raise SenderVerificationError("The verification token is invalid or expired.")

    with transaction.atomic(), schema_context("public"):
        locked_tenant = Tenant.objects.select_for_update().get(pk=tenant.pk)
        expires_at = locked_tenant.email_sender_verification_expires_at
        token_hash = locked_tenant.email_sender_verification_token_hash
        if (
            not token_hash
            or not expires_at
            or expires_at <= timezone.now()
            or not hmac.compare_digest(token_hash, _hash_token(token))
        ):
            raise SenderVerificationError("The verification token is invalid or expired.")

        verified_at = timezone.now()
        locked_tenant.email_sender_verified_at = verified_at
        locked_tenant.email_sender_verification_token_hash = ""
        locked_tenant.email_sender_verification_expires_at = None
        locked_tenant.save(
            update_fields=[
                "email_sender_verified_at",
                "email_sender_verification_token_hash",
                "email_sender_verification_expires_at",
            ]
        )
        return verified_at


def _hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
