from django.core.management import get_commands


def test_tenant_management_commands_are_unambiguous():
    commands = get_commands()

    assert commands["create_tenant"] == "django_tenants"
    assert commands["provision_tenant"] == "core"
