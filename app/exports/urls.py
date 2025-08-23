from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AssessmentReportViewSet

router = DefaultRouter()
router.register(r'assessment-reports', AssessmentReportViewSet, basename='assessment-reports')

urlpatterns = [
    path('', include(router.urls)),
]