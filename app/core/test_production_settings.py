"""Production settings regression tests."""

from pathlib import Path


def test_production_settings_do_not_print_allowed_hosts():
    production_settings = Path("app/settings/production.py").read_text()

    assert "print(f\"Production settings loaded" not in production_settings
    assert "Allowed hosts" not in production_settings


def test_production_settings_use_explicit_origin_allowlists():
    production_settings = Path("app/settings/production.py").read_text()

    assert "CORS_ALLOWED_ORIGINS = _csv_env('CORS_ALLOWED_ORIGINS')" in production_settings
    assert (
        "CSRF_TRUSTED_ORIGINS = _csv_env('CSRF_TRUSTED_ORIGINS') or CORS_ALLOWED_ORIGINS"
        in production_settings
    )
    assert "CORS_ALLOW_ALL_ORIGINS" not in production_settings
