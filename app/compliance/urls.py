from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    GovernanceArtefactViewSet,
    ManagementReviewViewSet,
    NonConformityViewSet,
    RegulatoryRequirementViewSet,
)

router = DefaultRouter()
router.register(r'artefacts', GovernanceArtefactViewSet, basename='governance-artefacts')
router.register(r'regulatory-requirements', RegulatoryRequirementViewSet, basename='regulatory-requirements')
router.register(r'non-conformities', NonConformityViewSet, basename='non-conformities')
router.register(r'management-reviews', ManagementReviewViewSet, basename='management-reviews')

app_name = 'compliance'

urlpatterns = [
    path('', include(router.urls)),
]
