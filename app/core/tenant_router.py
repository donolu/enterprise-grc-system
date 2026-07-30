from django.db import connections
from django_tenants.routers import TenantSyncRouter
from django_tenants.utils import get_public_schema_name, get_tenant_database_alias


class CoreModelTenantSyncRouter(TenantSyncRouter):
    """Route mixed core models to the schema class they actually belong to."""

    SHARED_ONLY_CORE_MODELS = {
        "billingevent",
        "domain",
        "limitoverriderequest",
        "plan",
        "subscription",
        "tenant",
    }
    TENANT_ONLY_CORE_MODELS = {
        "auditevent",
        "document",
        "documentaccess",
        "user",
    }

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db != get_tenant_database_alias():
            return False

        if app_label == "core" and model_name:
            schema_name = getattr(connections[db], "schema_name", get_public_schema_name())
            model_key = model_name.lower()
            if schema_name == get_public_schema_name():
                return model_key in self.SHARED_ONLY_CORE_MODELS
            return model_key in self.TENANT_ONLY_CORE_MODELS

        return super().allow_migrate(db, app_label, model_name=model_name, **hints)


class TestTenantSyncRouter(TenantSyncRouter):
    """Keep legacy unit tests on a single migrated public test schema."""

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db != get_tenant_database_alias():
            return False
        return True
