from django_tenants.utils import schema_context

from core.models import Tenant


def get_public_tenant(schema_name):
    """Return the tenant billing record from the public schema."""
    with schema_context("public"):
        return Tenant.objects.select_related("subscription__plan").get(
            schema_name=schema_name
        )
