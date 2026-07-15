from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AssetReviewReminderLogViewSet, AssetViewSet

router = DefaultRouter()
router.register(r'assets', AssetViewSet, basename='assets')
router.register(r'review-reminders', AssetReviewReminderLogViewSet, basename='asset-review-reminders')

app_name = 'assets'

urlpatterns = [
    path('', include(router.urls)),
]
