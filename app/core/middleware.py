from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin
from .models import Tenant
from threading import local

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
