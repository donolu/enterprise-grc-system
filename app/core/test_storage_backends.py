"""Tests for portable storage and deployment configuration helpers."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from django.core.files.base import ContentFile
from django.db import connection

from app.settings import base as settings_base
from core.storage import TenantAwareBlobStorage, TenantAwareFileSystemStorage, TenantAwareS3Storage


def test_database_url_is_parsed_for_tenant_postgres_backend():
    config = settings_base._database_config_from_url(
        "postgres://grc:p%40ss@db.example.com:6543/grc_prod?sslmode=require",
    )

    assert config == {
        "ENGINE": "django_tenants.postgresql_backend",
        "NAME": "grc_prod",
        "USER": "grc",
        "PASSWORD": "p@ss",
        "HOST": "db.example.com",
        "PORT": "6543",
        "OPTIONS": {"sslmode": "require"},
    }


def test_storage_backend_path_selects_s3(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "s3")

    assert settings_base._storage_backend_path() == "core.storage.TenantAwareS3Storage"


def test_storage_backend_path_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "ftp")

    with pytest.raises(ValueError, match="Unsupported STORAGE_BACKEND"):
        settings_base._storage_backend_path()


def test_filesystem_storage_saves_under_tenant_prefix(tmp_path, monkeypatch):
    monkeypatch.setattr(connection, "tenant", SimpleNamespace(slug="acme"), raising=False)
    storage = TenantAwareFileSystemStorage(location=tmp_path)

    saved_name = storage._save("reports/risk.pdf", ContentFile(b"risk report"))

    assert saved_name == "reports/risk.pdf"
    assert (Path(tmp_path) / "tenant-acme" / "reports" / "risk.pdf").read_bytes() == b"risk report"
    assert storage.exists("reports/risk.pdf") is True


def test_s3_storage_uses_tenant_prefix(monkeypatch):
    monkeypatch.setattr(connection, "tenant", SimpleNamespace(slug="acme"), raising=False)
    storage = TenantAwareS3Storage(bucket_name="grc-documents")

    assert storage._tenant_key("evidence/control.pdf") == "tenant-acme/evidence/control.pdf"


def test_azure_storage_uses_tenant_fallback_when_unavailable(tmp_path, monkeypatch, settings):
    monkeypatch.setattr(connection, "tenant", SimpleNamespace(slug="acme"), raising=False)
    settings.MEDIA_ROOT = tmp_path
    storage = TenantAwareBlobStorage()
    monkeypatch.setattr(storage, "_is_azure_available", lambda: False)

    saved_name = storage._save("evidence/control.txt", ContentFile(b"control evidence"))

    assert saved_name == "evidence/control.txt"
    assert storage._open("evidence/control.txt").read() == b"control evidence"
    assert storage.exists("evidence/control.txt") is True
