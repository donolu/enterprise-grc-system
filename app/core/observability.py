"""Runtime observability helpers for Sentry context and Prometheus metrics."""

from __future__ import annotations

import os
import time
from collections import defaultdict
from threading import Lock
from typing import Any

from django.conf import settings
from django.http import HttpRequest

_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
_METRIC_LOCK = Lock()
_HTTP_TOTAL: dict[tuple[str, str, str], int] = defaultdict(int)
_HTTP_LATENCY_BUCKETS: dict[tuple[str, str, float], int] = defaultdict(int)
_HTTP_LATENCY_SUM: dict[tuple[str, str], float] = defaultdict(float)
_HTTP_LATENCY_COUNT: dict[tuple[str, str], int] = defaultdict(int)
_CELERY_TOTAL: dict[tuple[str, str], int] = defaultdict(int)
_CELERY_LATENCY_BUCKETS: dict[tuple[str, str, float], int] = defaultdict(int)
_CELERY_LATENCY_SUM: dict[tuple[str, str], float] = defaultdict(float)
_CELERY_LATENCY_COUNT: dict[tuple[str, str], int] = defaultdict(int)
_CELERY_TASK_STARTS: dict[str, float] = {}
_CELERY_METRICS_REGISTERED = False


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def configure_sentry() -> bool:
    """Initialise Sentry when a DSN is supplied."""
    dsn = os.environ.get("SENTRY_DSN") or os.environ.get("DJANGO_SENTRY_DSN")
    if not dsn:
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.django import DjangoIntegration
    except ImportError:
        return False

    sentry_sdk.init(
        dsn=dsn,
        integrations=[
            DjangoIntegration(transaction_style="url"),
            CeleryIntegration(),
        ],
        environment=os.environ.get("SENTRY_ENVIRONMENT")
        or os.environ.get("DJANGO_ENVIRONMENT")
        or os.environ.get("DJANGO_SETTINGS_MODULE", "unknown"),
        release=os.environ.get("SENTRY_RELEASE")
        or os.environ.get("GITHUB_SHA")
        or os.environ.get("APP_VERSION"),
        traces_sample_rate=_env_float("SENTRY_TRACES_SAMPLE_RATE", 0.0),
        profiles_sample_rate=_env_float("SENTRY_PROFILES_SAMPLE_RATE", 0.0),
        send_default_pii=False,
    )
    return True


def attach_sentry_request_context(request: HttpRequest) -> None:
    """Attach non-PII tenant and user identifiers to the active Sentry scope."""
    if not getattr(settings, "SENTRY_ENABLED", False):
        return

    try:
        import sentry_sdk
    except ImportError:
        return

    tenant = getattr(request, "tenant", None)
    if tenant is not None:
        schema_name = getattr(tenant, "schema_name", None)
        slug = getattr(tenant, "slug", None)
        if schema_name:
            sentry_sdk.set_tag("tenant.schema", schema_name)
        if slug:
            sentry_sdk.set_tag("tenant.slug", slug)
        sentry_sdk.set_context(
            "tenant",
            {
                "schema_name": schema_name,
                "slug": slug,
            },
        )

    user = getattr(request, "user", None)
    if getattr(user, "is_authenticated", False):
        sentry_sdk.set_user({"id": str(user.pk)})


def request_route_label(request: HttpRequest) -> str:
    """Return a low-cardinality route label for request metrics."""
    resolver_match = getattr(request, "resolver_match", None)
    if resolver_match and resolver_match.view_name:
        return resolver_match.view_name
    return request.path


def record_http_request(method: str, route: str, status_code: int, duration: float) -> None:
    status = str(status_code)
    route_key = route or "unknown"
    method_key = method.upper()
    with _METRIC_LOCK:
        _HTTP_TOTAL[(method_key, route_key, status)] += 1
        _HTTP_LATENCY_SUM[(method_key, route_key)] += duration
        _HTTP_LATENCY_COUNT[(method_key, route_key)] += 1
        for bucket in _BUCKETS:
            if duration <= bucket:
                _HTTP_LATENCY_BUCKETS[(method_key, route_key, bucket)] += 1
        _HTTP_LATENCY_BUCKETS[(method_key, route_key, float("inf"))] += 1


def register_celery_metrics() -> None:
    """Register Celery signal handlers for task count and latency metrics."""
    global _CELERY_METRICS_REGISTERED
    if _CELERY_METRICS_REGISTERED:
        return

    try:
        from celery import signals
    except ImportError:
        return

    signals.task_prerun.connect(_celery_task_prerun, weak=False)
    signals.task_postrun.connect(_celery_task_postrun, weak=False)
    _CELERY_METRICS_REGISTERED = True


def _celery_task_prerun(
    task_id: str | None = None,
    **_: Any,
) -> None:
    if not task_id:
        return
    with _METRIC_LOCK:
        _CELERY_TASK_STARTS[task_id] = time.perf_counter()


def _celery_task_postrun(
    task_id: str | None = None,
    task: Any = None,
    state: str | None = None,
    **_: Any,
) -> None:
    task_name = getattr(task, "name", None) or "unknown"
    status = (state or "unknown").lower()
    duration = 0.0
    if task_id:
        with _METRIC_LOCK:
            started_at = _CELERY_TASK_STARTS.pop(task_id, None)
        if started_at is not None:
            duration = time.perf_counter() - started_at
    record_celery_task(task_name, status, duration)


def record_celery_task(task_name: str, status: str, duration: float) -> None:
    task_key = task_name or "unknown"
    status_key = status or "unknown"
    with _METRIC_LOCK:
        _CELERY_TOTAL[(task_key, status_key)] += 1
        _CELERY_LATENCY_SUM[(task_key, status_key)] += duration
        _CELERY_LATENCY_COUNT[(task_key, status_key)] += 1
        for bucket in _BUCKETS:
            if duration <= bucket:
                _CELERY_LATENCY_BUCKETS[(task_key, status_key, bucket)] += 1
        _CELERY_LATENCY_BUCKETS[(task_key, status_key, float("inf"))] += 1


def render_prometheus_metrics() -> str:
    with _METRIC_LOCK:
        http_total = dict(_HTTP_TOTAL)
        http_buckets = dict(_HTTP_LATENCY_BUCKETS)
        http_sum = dict(_HTTP_LATENCY_SUM)
        http_count = dict(_HTTP_LATENCY_COUNT)
        celery_total = dict(_CELERY_TOTAL)
        celery_buckets = dict(_CELERY_LATENCY_BUCKETS)
        celery_sum = dict(_CELERY_LATENCY_SUM)
        celery_count = dict(_CELERY_LATENCY_COUNT)

    lines = [
        "# HELP grc_http_requests_total Total HTTP requests by method, route, and status.",
        "# TYPE grc_http_requests_total counter",
    ]
    for (method, route, status), count in sorted(http_total.items()):
        lines.append(
            'grc_http_requests_total{'
            f'method="{_escape_label(method)}",route="{_escape_label(route)}",'
            f'status="{_escape_label(status)}"'
            f"}} {count}"
        )

    lines.extend(
        [
            "# HELP grc_http_request_duration_seconds HTTP request duration.",
            "# TYPE grc_http_request_duration_seconds histogram",
        ]
    )
    for method, route in sorted(http_count):
        for bucket in (*_BUCKETS, float("inf")):
            count = http_buckets.get((method, route, bucket), 0)
            lines.append(
                'grc_http_request_duration_seconds_bucket{'
                f'method="{_escape_label(method)}",route="{_escape_label(route)}",'
                f'le="{_format_bucket(bucket)}"'
                f"}} {count}"
            )
        labels = f'method="{_escape_label(method)}",route="{_escape_label(route)}"'
        lines.append(f"grc_http_request_duration_seconds_sum{{{labels}}} {http_sum[(method, route)]:.6f}")
        lines.append(f"grc_http_request_duration_seconds_count{{{labels}}} {http_count[(method, route)]}")

    lines.extend(
        [
            "# HELP grc_celery_tasks_total Total Celery tasks by task name and status.",
            "# TYPE grc_celery_tasks_total counter",
        ]
    )
    for (task_name, status), count in sorted(celery_total.items()):
        lines.append(
            'grc_celery_tasks_total{'
            f'task="{_escape_label(task_name)}",status="{_escape_label(status)}"'
            f"}} {count}"
        )

    lines.extend(
        [
            "# HELP grc_celery_task_duration_seconds Celery task duration.",
            "# TYPE grc_celery_task_duration_seconds histogram",
        ]
    )
    for task_name, status in sorted(celery_count):
        for bucket in (*_BUCKETS, float("inf")):
            count = celery_buckets.get((task_name, status, bucket), 0)
            lines.append(
                'grc_celery_task_duration_seconds_bucket{'
                f'task="{_escape_label(task_name)}",status="{_escape_label(status)}",'
                f'le="{_format_bucket(bucket)}"'
                f"}} {count}"
            )
        labels = f'task="{_escape_label(task_name)}",status="{_escape_label(status)}"'
        lines.append(f"grc_celery_task_duration_seconds_sum{{{labels}}} {celery_sum[(task_name, status)]:.6f}")
        lines.append(f"grc_celery_task_duration_seconds_count{{{labels}}} {celery_count[(task_name, status)]}")

    return "\n".join(lines) + "\n"


def reset_observability_metrics() -> None:
    """Clear process metrics. Intended for tests."""
    with _METRIC_LOCK:
        _HTTP_TOTAL.clear()
        _HTTP_LATENCY_BUCKETS.clear()
        _HTTP_LATENCY_SUM.clear()
        _HTTP_LATENCY_COUNT.clear()
        _CELERY_TOTAL.clear()
        _CELERY_LATENCY_BUCKETS.clear()
        _CELERY_LATENCY_SUM.clear()
        _CELERY_LATENCY_COUNT.clear()
        _CELERY_TASK_STARTS.clear()


def _format_bucket(bucket: float) -> str:
    return "+Inf" if bucket == float("inf") else f"{bucket:g}"


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
