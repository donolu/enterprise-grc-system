"""
URL configuration for core app including document management.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentViewSet
from .health import HealthCheckView, ReadinessCheckView, LivenessCheckView, StartupCheckView

app_name = 'core'

# API Router
router = DefaultRouter()
router.register('documents', DocumentViewSet, basename='documents')

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    # Health check endpoints
    path('health/', HealthCheckView.as_view(), name='health_check'),
    path('health/ready/', ReadinessCheckView.as_view(), name='readiness_check'),
    path('health/live/', LivenessCheckView.as_view(), name='liveness_check'),
    path('health/startup/', StartupCheckView.as_view(), name='startup_check'),
]