#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR/app"

export PYTHONPATH="$ROOT_DIR/app${PYTHONPATH:+:$PYTHONPATH}"

python manage.py migrate_schemas --shared

python manage.py shell <<'PY'
from core.models import Domain, Tenant
from django.core.management import call_command
from django_tenants.utils import schema_context

tenant, _ = Tenant.objects.get_or_create(
    schema_name="test",
    defaults={"name": "Test Company", "slug": "test"},
)
Domain.objects.update_or_create(
    domain="test.localhost",
    defaults={"tenant": tenant, "is_primary": True},
)

with schema_context(tenant.schema_name):
    call_command("migrate", interactive=False, verbosity=1)

print("Test tenant created successfully")
PY
