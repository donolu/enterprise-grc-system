"""
URL configuration for core app including document management.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentViewSet

app_name = 'core'

# API Router
router = DefaultRouter()
router.register('documents', DocumentViewSet, basename='documents')

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
]