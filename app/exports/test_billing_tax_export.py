import pytest
from django_tenants.utils import schema_context

from core.models import InvoiceEvidence
from exports.models import TenantDataExport
from exports.services import TenantDataExportGenerator, get_export_coverage_manifest


@pytest.mark.django_db
def test_billing_tax_export_covers_invoice_evidence_only(test_tenant, admin_user):
    with schema_context("public"):
        InvoiceEvidence.objects.create(
            stripe_invoice_id="in_export_123",
            tenant=test_tenant,
            invoice_number="INV-0001",
            status="paid",
            currency="gbp",
            subtotal=10000,
            tax_amount=2000,
            total=12000,
        )
        data_export = TenantDataExport(
            requested_by=admin_user,
            selected_modules=["billing_tax"],
        )
        sheets = list(TenantDataExportGenerator(data_export)._iter_sheet_data())

    assert [sheet[0] for sheet in sheets] == ["Invoice tax evidence"]
    assert sheets[0][3] == "core.InvoiceEvidence"
    values = dict(zip(sheets[0][1], sheets[0][2][0], strict=True))
    assert values["stripe_invoice_id"] == "in_export_123"
    assert values["tenant"] == str(test_tenant.id)
    assert values["invoice_number"] == "INV-0001"
    assert values["status"] == "paid"
    assert values["tax_amount"] == "2000"


def test_billing_tax_module_is_documented_in_export_manifest():
    modules = {entry["module"]: entry for entry in get_export_coverage_manifest()}

    assert modules["billing_tax"]["formats"] == ["xlsx", "csv_zip"]
    assert modules["billing_tax"]["sheets"] == [
        {"model": "core.InvoiceEvidence", "worksheet": "Invoice tax evidence"}
    ]
