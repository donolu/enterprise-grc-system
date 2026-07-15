from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ScanJobViewSet, ScanScheduleViewSet, ScanTargetViewSet, VulnerabilityFindingViewSet

router = DefaultRouter()
router.register(r'targets', ScanTargetViewSet, basename='scan-target')
router.register(r'schedules', ScanScheduleViewSet, basename='scan-schedule')
router.register(r'jobs', ScanJobViewSet, basename='scan-job')
router.register(r'findings', VulnerabilityFindingViewSet, basename='vulnerability-finding')

app_name = 'vuln'

urlpatterns = [
    path('', include(router.urls)),
]
