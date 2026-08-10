from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django_tenants.utils import schema_context

from core.models import Plan


@pytest.mark.django_db
def test_checkout_enables_stripe_tax_and_tax_id_collection(tenant_client, test_tenant, admin_user):
    with schema_context("public"):
        Plan.objects.create(
            name="Basic",
            slug="basic",
            price_monthly=49,
            stripe_price_id="price_basic",
        )

    tenant_client.force_authenticate(user=admin_user)
    customer = SimpleNamespace(id="cus_test_123")
    session = SimpleNamespace(id="cs_test_123", url="https://checkout.stripe.test/session")

    with (
        patch("billing.views.stripe.Customer.create", return_value=customer),
        patch("billing.views.stripe.checkout.Session.create", return_value=session) as create,
    ):
        response = tenant_client.post(
            "/api/billing/create_checkout_session/",
            {"plan": "basic"},
            format="json",
        )

    assert response.status_code == 200
    assert create.call_args.kwargs["automatic_tax"] == {"enabled": True}
    assert create.call_args.kwargs["billing_address_collection"] == "required"
    assert create.call_args.kwargs["tax_id_collection"] == {"enabled": True}
    assert create.call_args.kwargs["customer_update"] == {
        "address": "auto",
        "name": "auto",
    }
