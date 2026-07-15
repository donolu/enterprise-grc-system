from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import KnowledgeArticleViewSet, KnowledgeCategoryViewSet

router = DefaultRouter()
router.register(r'categories', KnowledgeCategoryViewSet, basename='knowledge-categories')
router.register(r'articles', KnowledgeArticleViewSet, basename='knowledge-articles')

app_name = 'knowledge'

urlpatterns = [
    path('', include(router.urls)),
]
