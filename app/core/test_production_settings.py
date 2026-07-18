"""Production settings regression tests."""

from pathlib import Path

PRODUCTION_SETTINGS = Path(__file__).resolve().parents[1] / "app/settings/production.py"


def test_production_settings_do_not_print_allowed_hosts():
    production_settings = PRODUCTION_SETTINGS.read_text()

    assert "print(f\"Production settings loaded" not in production_settings
    assert "Allowed hosts" not in production_settings


def test_production_settings_use_explicit_origin_allowlists():
    production_settings = PRODUCTION_SETTINGS.read_text()

    assert "CORS_ALLOWED_ORIGINS = _csv_env('CORS_ALLOWED_ORIGINS')" in production_settings
    assert (
        "CSRF_TRUSTED_ORIGINS = _csv_env('CSRF_TRUSTED_ORIGINS') or CORS_ALLOWED_ORIGINS"
        in production_settings
    )
    assert "CORS_ALLOW_ALL_ORIGINS" not in production_settings


def test_production_metrics_require_bearer_token_to_be_enabled():
    production_settings = PRODUCTION_SETTINGS.read_text()

    assert "METRICS_BEARER_TOKEN = os.environ.get('METRICS_BEARER_TOKEN', '')" in production_settings
    assert "and bool(METRICS_BEARER_TOKEN)" in production_settings
