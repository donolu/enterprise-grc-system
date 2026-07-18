import time
from threading import local

from django.utils.deprecation import MiddlewareMixin

from .models import Tenant
from .observability import (
    attach_sentry_request_context,
    record_http_request,
    request_route_label,
)

_tl = local()


def get_current_tenant():
    return getattr(_tl, "tenant", None)


class TenantResolveMiddleware(MiddlewareMixin):
    def process_request(self, request):
        mode = request.headers.get("X-Tenancy-Mode") or "subdomain"
        tenant = None
        if mode == "header":
            slug = request.headers.get("X-Tenant-Id")
            if slug:
                tenant = Tenant.objects.filter(slug=slug).first()
        else:
            host = request.get_host().split(":")[0]
            parts = host.split(".")
            if len(parts) > 2:
                slug = parts[0]
                tenant = Tenant.objects.filter(slug=slug).first()
        if not tenant:
            pass
        _tl.tenant = tenant


class ObservabilityMiddleware:
    """Attach request context to Sentry and record request metrics."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        attach_sentry_request_context(request)
        started_at = time.perf_counter()
        try:
            response = self.get_response(request)
        except Exception:
            duration = time.perf_counter() - started_at
            record_http_request(
                request.method,
                request_route_label(request),
                500,
                duration,
            )
            raise

        duration = time.perf_counter() - started_at
        record_http_request(
            request.method,
            request_route_label(request),
            response.status_code,
            duration,
        )
        return response
