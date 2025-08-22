from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'frameworks', views.FrameworkViewSet)
router.register(r'clauses', views.ClauseViewSet)
router.register(r'controls', views.ControlViewSet)
router.register(r'evidence', views.ControlEvidenceViewSet)
router.register(r'mappings', views.FrameworkMappingViewSet)

app_name = 'catalogs'

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    # Additional stats endpoint
    path('api/stats/', views.framework_stats, name='framework-stats'),
]