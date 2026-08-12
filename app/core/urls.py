"""
URL configuration for core app including document management.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AuditEventViewSet,
    DocumentViewSet,
    TenantEmailSettingsView,
    TenantEmailVerificationConfirmView,
    TenantEmailVerificationRequestView,
    TenantTaxProfileView,
    GlobalSearchView,
)
from .health import (
    HealthCheckView,
    LivenessCheckView,
    MetricsView,
    ReadinessCheckView,
    StartupCheckView,
)

app_name = "core"

# API Router
router = DefaultRouter()
router.register("documents", DocumentViewSet, basename="documents")
router.register("audit-events", AuditEventViewSet, basename="audit-events")

urlpatterns = [
    # API endpoints
    path("api/", include(router.urls)),
    path("api/search/", GlobalSearchView.as_view(), name="global-search"),
    path(
        "api/tenant-email-settings/",
        TenantEmailSettingsView.as_view(),
        name="tenant-email-settings",
    ),
    path(
        "api/tenant-email-settings/verification/",
        TenantEmailVerificationRequestView.as_view(),
        name="tenant-email-verification-request",
    ),
    path(
        "api/tenant-email-settings/verification/confirm/",
        TenantEmailVerificationConfirmView.as_view(),
        name="tenant-email-verification-confirm",
    ),
    path(
        "api/tenant-tax-profile/",
        TenantTaxProfileView.as_view(),
        name="tenant-tax-profile",
    ),
    # Health check endpoints
    path("health/", HealthCheckView.as_view(), name="health_check"),
    path("health/ready/", ReadinessCheckView.as_view(), name="readiness_check"),
    path("health/live/", LivenessCheckView.as_view(), name="liveness_check"),
    path("health/startup/", StartupCheckView.as_view(), name="startup_check"),
    path("metrics/", MetricsView.as_view(), name="metrics"),
]
