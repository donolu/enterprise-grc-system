from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RiskViewSet, RiskCategoryViewSet, RiskMatrixViewSet,
    RiskActionViewSet, RiskActionReminderConfigurationViewSet,
    RiskAnalyticsViewSet
)

router = DefaultRouter()
router.register(r'risks', RiskViewSet, basename='risk')
router.register(r'categories', RiskCategoryViewSet, basename='riskcategory')
router.register(r'matrices', RiskMatrixViewSet, basename='riskmatrix')
router.register(r'actions', RiskActionViewSet, basename='riskaction')
router.register(r'reminder-config', RiskActionReminderConfigurationViewSet, basename='riskactionreminderconfig')
router.register(r'analytics', RiskAnalyticsViewSet, basename='riskanalytics')

urlpatterns = [
    path('', include(router.urls)),
]