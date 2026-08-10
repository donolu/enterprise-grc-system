import pytest
from django_tenants.utils import schema_context

from billing.views import StripeWebhookView
from core.models import InvoiceEvidence


@pytest.mark.django_db
def test_invoice_event_persists_redacted_tax_evidence(test_tenant):
    invoice = {
        "id": "in_test_123",
        "customer": "cus_test_123",
        "number": "INV-0001",
        "status": "paid",
        "currency": "gbp",
        "subtotal": 10000,
        "total_taxes": [{"amount": 2000}],
        "total": 12000,
        "amount_due": 12000,
        "amount_paid": 12000,
        "hosted_invoice_url": "https://invoice.stripe.test/hosted",
        "invoice_pdf": "https://invoice.stripe.test/pdf",
        "automatic_tax": {"status": "complete"},
        "period_start": 1_755_000_000,
        "period_end": 1_757_600_000,
    }

    with schema_context("public"):
        test_tenant.stripe_customer_id = "cus_test_123"
        test_tenant.save(update_fields=["stripe_customer_id"])
        StripeWebhookView()._handle_invoice_event(invoice, "evt_invoice_123")
        evidence = InvoiceEvidence.objects.get(stripe_invoice_id="in_test_123")

        assert evidence.tenant_id == test_tenant.id
        assert evidence.tax_amount == 2000
        assert evidence.total == 12000
        assert evidence.tax_status == "complete"
