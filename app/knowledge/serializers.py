from rest_framework import serializers

from .models import KnowledgeArticle, KnowledgeArticleRevision, KnowledgeCategory, MODULE_CHOICES


class KnowledgeCategorySerializer(serializers.ModelSerializer):
    article_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = KnowledgeCategory
        fields = [
            'id', 'name', 'slug', 'description', 'module_key', 'sort_order',
            'is_active', 'article_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class KnowledgeArticleListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = KnowledgeArticle
        fields = [
            'id', 'title', 'slug', 'summary', 'category', 'category_name',
            'module_key', 'workflow_key', 'tags', 'status', 'content_scope',
            'sort_order', 'published_at', 'updated_at',
        ]
        read_only_fields = ['published_at', 'updated_at']


class KnowledgeArticleDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    updated_by_username = serializers.CharField(source='updated_by.username', read_only=True)

    class Meta:
        model = KnowledgeArticle
        fields = [
            'id', 'title', 'slug', 'summary', 'body', 'category', 'category_name',
            'module_key', 'workflow_key', 'tags', 'status', 'content_scope',
            'sort_order', 'published_at', 'created_by_username',
            'updated_by_username', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'published_at', 'created_by_username', 'updated_by_username',
            'created_at', 'updated_at',
        ]

    def validate_module_key(self, value):
        valid_modules = {choice[0] for choice in MODULE_CHOICES}
        if value and value not in valid_modules:
            raise serializers.ValidationError('Unsupported module key.')
        return value

    def validate_tags(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Tags must be a list.')
        return [str(tag).strip() for tag in value if str(tag).strip()]


class KnowledgeArticleRevisionSerializer(serializers.ModelSerializer):
    changed_by_username = serializers.CharField(source='changed_by.username', read_only=True)

    class Meta:
        model = KnowledgeArticleRevision
        fields = [
            'id', 'article', 'title', 'summary', 'body', 'status',
            'changed_by_username', 'changed_at',
        ]
