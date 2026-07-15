from django.contrib import admin

from .models import KnowledgeArticle, KnowledgeArticleRevision, KnowledgeCategory


@admin.register(KnowledgeCategory)
class KnowledgeCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'module_key', 'is_active', 'sort_order', 'updated_at')
    list_filter = ('is_active', 'module_key')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}


class KnowledgeArticleRevisionInline(admin.TabularInline):
    model = KnowledgeArticleRevision
    extra = 0
    readonly_fields = ('title', 'status', 'changed_by', 'changed_at')
    fields = ('title', 'status', 'changed_by', 'changed_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(KnowledgeArticle)
class KnowledgeArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'module_key', 'workflow_key', 'status', 'content_scope', 'updated_at')
    list_filter = ('status', 'content_scope', 'module_key', 'category')
    search_fields = ('title', 'summary', 'body', 'workflow_key')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [KnowledgeArticleRevisionInline]


@admin.register(KnowledgeArticleRevision)
class KnowledgeArticleRevisionAdmin(admin.ModelAdmin):
    list_display = ('article', 'status', 'changed_by', 'changed_at')
    list_filter = ('status', 'changed_at')
    search_fields = ('article__title', 'title', 'body')
    readonly_fields = ('article', 'title', 'summary', 'body', 'status', 'changed_by', 'changed_at')
