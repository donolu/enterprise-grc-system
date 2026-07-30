from django.db import connections

from core.tenant_router import CoreModelTenantSyncRouter
from sso.models import SSOProvider


def _allow_core_model(schema_name, model_name):
    connection = connections["default"]
    original_schema_name = getattr(connection, "schema_name", "public")
    connection.schema_name = schema_name
    try:
        return CoreModelTenantSyncRouter().allow_migrate("default", "core", model_name)
    finally:
        connection.schema_name = original_schema_name


def test_core_public_schema_only_migrates_shared_metadata_models():
    assert _allow_core_model("public", "tenant") is True
    assert _allow_core_model("public", "plan") is True

    assert _allow_core_model("public", "user") is False
    assert _allow_core_model("public", "document") is False
    assert _allow_core_model("public", "auditevent") is False


def test_core_tenant_schema_only_migrates_tenant_owned_models():
    assert _allow_core_model("tenant_a", "user") is True
    assert _allow_core_model("tenant_a", "document") is True
    assert _allow_core_model("tenant_a", "auditevent") is True

    assert _allow_core_model("tenant_a", "tenant") is False
    assert _allow_core_model("tenant_a", "plan") is False
    assert _allow_core_model("tenant_a", "subscription") is False


def test_sso_provider_tenant_reference_does_not_require_local_tenant_table():
    assert SSOProvider._meta.get_field("tenant").db_constraint is False
