"""
Policy Repository URL Configuration
"""

from rest_framework.routers import DefaultRouter
from .views import (
    PolicyCategoryViewSet,
    PolicyViewSet,
    PolicyVersionViewSet,
    PolicyAcknowledgmentViewSet,
    PolicyDistributionViewSet
)

router = DefaultRouter()
router.register(r'categories', PolicyCategoryViewSet)
router.register(r'policies', PolicyViewSet, basename='policy')
router.register(r'versions', PolicyVersionViewSet, basename='policyversion')
router.register(r'acknowledgments', PolicyAcknowledgmentViewSet, basename='policyacknowledgment')
router.register(r'distributions', PolicyDistributionViewSet, basename='policydistribution')

urlpatterns = router.urls