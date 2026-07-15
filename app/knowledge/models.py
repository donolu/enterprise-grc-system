from django.conf import settings
from django.db import models
from django.utils import timezone


MODULE_CHOICES = [
    ('dashboard', 'Dashboard'),
    ('frameworks', 'Frameworks and assessments'),
    ('risk', 'Risk'),
    ('assets', 'Assets'),
    ('vendors', 'Vendors'),
    ('policies', 'Policies'),
    ('training', 'Training'),
    ('analytics', 'Analytics'),
    ('vulnerability_scanning', 'Vulnerability scanning'),
    ('exports', 'Exports'),
    ('administration', 'Administration'),
]


class KnowledgeCategory(models.Model):
    """
    Tenant-scoped category for organising help and guidance articles.
    """

    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    module_key = models.CharField(max_length=50, choices=MODULE_CHOICES, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_knowledge_categories',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name_plural = 'Knowledge categories'
        indexes = [
            models.Index(fields=['is_active', 'module_key']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return self.name


class KnowledgeArticle(models.Model):
    """
    Tenant-visible help article with publishing workflow and optional module context.
    """

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]

    CONTENT_SCOPE_CHOICES = [
        ('tenant', 'Tenant'),
        ('global', 'Axim-managed global'),
    ]

    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True)
    summary = models.TextField(blank=True)
    body = models.TextField()
    category = models.ForeignKey(
        KnowledgeCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='articles',
    )
    module_key = models.CharField(max_length=50, choices=MODULE_CHOICES, blank=True)
    workflow_key = models.CharField(max_length=80, blank=True)
    tags = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    content_scope = models.CharField(max_length=20, choices=CONTENT_SCOPE_CHOICES, default='tenant')
    sort_order = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_knowledge_articles',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_knowledge_articles',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'title']
        indexes = [
            models.Index(fields=['status', 'module_key']),
            models.Index(fields=['content_scope', 'status']),
            models.Index(fields=['slug']),
            models.Index(fields=['workflow_key']),
        ]

    def __str__(self):
        return self.title

    @property
    def is_published(self):
        return self.status == 'published'

    def save(self, *args, **kwargs):
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        if self.status != 'published':
            self.published_at = None
        super().save(*args, **kwargs)


class KnowledgeArticleRevision(models.Model):
    """
    Lightweight audit trail of article content changes.
    """

    article = models.ForeignKey(
        KnowledgeArticle,
        on_delete=models.CASCADE,
        related_name='revisions',
    )
    title = models.CharField(max_length=220)
    summary = models.TextField(blank=True)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=KnowledgeArticle.STATUS_CHOICES)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='knowledge_article_revisions',
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['article', '-changed_at']),
        ]

    def __str__(self):
        return f'{self.article.title} revision at {self.changed_at:%Y-%m-%d %H:%M}'
