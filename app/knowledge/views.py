from django.db.models import Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import KnowledgeArticle, KnowledgeArticleRevision, KnowledgeCategory
from .serializers import (
    KnowledgeArticleDetailSerializer,
    KnowledgeArticleListSerializer,
    KnowledgeArticleRevisionSerializer,
    KnowledgeCategorySerializer,
)


class IsStaffOrReadPublished(permissions.BasePermission):
    """
    Allow staff to manage knowledge content and users to read published content.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff or request.user.is_superuser

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.is_superuser:
            return True
        if isinstance(obj, KnowledgeArticle):
            return obj.status == 'published'
        if isinstance(obj, KnowledgeCategory):
            return obj.is_active
        return request.method in permissions.SAFE_METHODS


class KnowledgePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class KnowledgeCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrReadPublished]
    serializer_class = KnowledgeCategorySerializer
    pagination_class = KnowledgePagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['module_key', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'sort_order', 'updated_at']
    ordering = ['sort_order', 'name']

    def get_queryset(self):
        queryset = KnowledgeCategory.objects.annotate(
            article_count=Count('articles', filter=Q(articles__status='published'))
        )
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            queryset = queryset.filter(is_active=True)
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class KnowledgeArticleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffOrReadPublished]
    pagination_class = KnowledgePagination
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'module_key', 'workflow_key', 'status', 'content_scope']
    search_fields = ['title', 'summary', 'body', 'tags']
    ordering_fields = ['title', 'sort_order', 'published_at', 'updated_at']
    ordering = ['sort_order', 'title']

    def get_queryset(self):
        queryset = KnowledgeArticle.objects.select_related('category', 'created_by', 'updated_by')
        if self.request.user.is_staff or self.request.user.is_superuser:
            return queryset
        return queryset.filter(status='published', category__is_active=True)

    def get_serializer_class(self):
        if self.action == 'list':
            return KnowledgeArticleListSerializer
        return KnowledgeArticleDetailSerializer

    def perform_create(self, serializer):
        article = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        self._record_revision(article)

    def perform_update(self, serializer):
        article = serializer.save(updated_by=self.request.user)
        self._record_revision(article)

    @action(detail=False, methods=['get'])
    def contextual(self, request):
        """Return published guidance for a module and optional workflow key."""
        module_key = request.query_params.get('module_key', '')
        workflow_key = request.query_params.get('workflow_key', '')
        if not module_key:
            return Response(
                {'module_key': ['This query parameter is required.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self.get_queryset().filter(module_key=module_key)
        if workflow_key:
            queryset = queryset.filter(Q(workflow_key=workflow_key) | Q(workflow_key=''))
        serializer = KnowledgeArticleListSerializer(queryset[:10], many=True)
        return Response({'results': serializer.data})

    @action(detail=True, methods=['get'])
    def revisions(self, request, slug=None):
        article = self.get_object()
        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {'detail': 'Only staff users can view article revisions.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = KnowledgeArticleRevisionSerializer(article.revisions.all(), many=True)
        return Response({'results': serializer.data})

    def _record_revision(self, article):
        KnowledgeArticleRevision.objects.create(
            article=article,
            title=article.title,
            summary=article.summary,
            body=article.body,
            status=article.status,
            changed_by=self.request.user,
        )
