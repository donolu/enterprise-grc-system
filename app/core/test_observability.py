from types import SimpleNamespace

import pytest
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from core.health import MetricsView
from core.middleware import ObservabilityMiddleware
from core.observability import (
    attach_sentry_request_context,
    record_celery_task,
    render_prometheus_metrics,
    reset_observability_metrics,
)


@pytest.fixture(autouse=True)
def clear_metrics():
    reset_observability_metrics()
    yield
    reset_observability_metrics()


def test_observability_middleware_records_http_request_metrics():
    request = RequestFactory().get("/observability-test/")
    middleware = ObservabilityMiddleware(lambda _: HttpResponse("ok", status=202))

    response = middleware(request)

    assert response.status_code == 202
    metrics = render_prometheus_metrics()
    assert (
        'grc_http_requests_total{method="GET",route="/observability-test/",'
        'status="202"} 1'
    ) in metrics
    assert (
        'grc_http_request_duration_seconds_count{method="GET",'
        'route="/observability-test/"} 1'
    ) in metrics


def test_metrics_endpoint_can_require_bearer_token():
    view = MetricsView.as_view()
    factory = RequestFactory()

    with override_settings(METRICS_ENABLED=True, METRICS_BEARER_TOKEN="secret"):
        unauthenticated = view(factory.get("/metrics/"))
        authenticated = view(
            factory.get("/metrics/", HTTP_AUTHORIZATION="Bearer secret")
        )

    assert unauthenticated.status_code == 401
    assert authenticated.status_code == 200
    assert authenticated["Content-Type"] == "text/plain; version=0.0.4; charset=utf-8"


def test_metrics_endpoint_accepts_x_metrics_token_header():
    view = MetricsView.as_view()
    factory = RequestFactory()

    with override_settings(METRICS_ENABLED=True, METRICS_BEARER_TOKEN="secret"):
        authenticated = view(factory.get("/metrics/", HTTP_X_METRICS_TOKEN="secret"))

    assert authenticated.status_code == 200


def test_celery_task_metrics_are_rendered():
    record_celery_task("risk.tasks.send_reminders", "success", 0.25)

    metrics = render_prometheus_metrics()

    assert (
        'grc_celery_tasks_total{task="risk.tasks.send_reminders",'
        'status="success"} 1'
    ) in metrics
    assert (
        'grc_celery_task_duration_seconds_count{task="risk.tasks.send_reminders",'
        'status="success"} 1'
    ) in metrics


def test_sentry_context_uses_non_pii_tenant_and_user_identifiers(monkeypatch):
    calls = {"tags": {}, "context": {}, "user": None}

    fake_sentry = SimpleNamespace(
        set_tag=lambda key, value: calls["tags"].__setitem__(key, value),
        set_context=lambda key, value: calls["context"].__setitem__(key, value),
        set_user=lambda value: calls.__setitem__("user", value),
    )
    monkeypatch.setitem(__import__("sys").modules, "sentry_sdk", fake_sentry)

    request = RequestFactory().get("/")
    request.tenant = SimpleNamespace(schema_name="tenant_123", slug="acme")
    request.user = SimpleNamespace(is_authenticated=True, pk=42, email="pii@example.com")

    with override_settings(SENTRY_ENABLED=True):
        attach_sentry_request_context(request)

    assert calls["tags"] == {
        "tenant.schema": "tenant_123",
        "tenant.slug": "acme",
    }
    assert calls["context"]["tenant"] == {
        "schema_name": "tenant_123",
        "slug": "acme",
    }
    assert calls["user"] == {"id": "42"}
