"""
Training URLs

URL configuration for security awareness training.
"""

from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import (
    TrainingCategoryViewSet,
    TrainingVideoViewSet,
    SecurityAwarenessCampaignViewSet,
    CampaignDeliveryViewSet,
    VideoViewViewSet,
    training_dashboard
)

router = DefaultRouter()
router.register(r'categories', TrainingCategoryViewSet)
router.register(r'videos', TrainingVideoViewSet, basename='trainingvideo')
router.register(r'campaigns', SecurityAwarenessCampaignViewSet, basename='securityawarenesscampaign')
router.register(r'deliveries', CampaignDeliveryViewSet, basename='campaigndelivery')
router.register(r'views', VideoViewViewSet, basename='videoview')

urlpatterns = [
    path('dashboard/', training_dashboard, name='training-dashboard'),
] + router.urls