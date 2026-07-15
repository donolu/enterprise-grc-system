from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AssessmentReportViewSet, TenantDataExportViewSet

router = DefaultRouter()
router.register(r'assessment-reports', AssessmentReportViewSet, basename='assessment-reports')
router.register(r'tenant-data-exports', TenantDataExportViewSet, basename='tenant-data-exports')

urlpatterns = [
    path('', include(router.urls)),
]
