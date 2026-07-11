"""
Analytics Models

Models for managing analytics reports, exports, and dashboard configurations.
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class AnalyticsReport(models.Model):
    """
    Model to track analytics report generation and export requests.
    """

    REPORT_TYPES = [
        ('executive', 'Executive Dashboard'),
        ('compliance', 'Compliance Analytics'),
        ('risk', 'Risk Management'),
        ('vendor', 'Vendor Risk Assessment'),
        ('policy', 'Policy Management'),
        ('training', 'Training Effectiveness'),
        ('integrated', 'Integrated Risk Posture'),
        ('operational', 'Operational Dashboard'),
    ]

    EXPORT_FORMATS = [
        ('pdf', 'PDF Report'),
        ('excel', 'Excel Spreadsheet'),
        ('csv', 'CSV Data Export'),
        ('json', 'JSON Data Export'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    export_format = models.CharField(max_length=20, choices=EXPORT_FORMATS)
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='analytics_reports')

    # Report configuration
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    date_range_start = models.DateField(null=True, blank=True)
    date_range_end = models.DateField(null=True, blank=True)
    filters = models.JSONField(default=dict, blank=True)  # Store filter parameters

    # Processing status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    # File output
    file_path = models.CharField(max_length=500, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)  # Size in bytes
    download_count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    generation_time_seconds = models.FloatField(null=True, blank=True)
    data_points_included = models.PositiveIntegerField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'analytics_reports'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['requested_by', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['report_type']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"{self.get_report_type_display()} ({self.get_export_format_display()}) - {self.status}"

    @property
    def is_expired(self):
        """Check if the report has expired."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

    @property
    def is_downloadable(self):
        """Check if the report is ready for download."""
        return (
            self.status == 'completed' and
            self.file_path and
            not self.is_expired
        )

    def mark_started(self):
        """Mark the report as started processing."""
        self.status = 'processing'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])

    def mark_completed(self, file_path, file_size=None, data_points=None):
        """Mark the report as completed."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.file_path = file_path
        self.file_size = file_size
        self.data_points_included = data_points

        # Calculate generation time
        if self.started_at:
            self.generation_time_seconds = (
                self.completed_at - self.started_at
            ).total_seconds()

        # Set expiration (reports expire after 30 days)
        self.expires_at = timezone.now() + timezone.timedelta(days=30)

        self.save(update_fields=[
            'status', 'completed_at', 'file_path', 'file_size',
            'data_points_included', 'generation_time_seconds', 'expires_at'
        ])

    def mark_failed(self, error_message):
        """Mark the report as failed with error message."""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message

        if self.started_at:
            self.generation_time_seconds = (
                self.completed_at - self.started_at
            ).total_seconds()

        self.save(update_fields=[
            'status', 'completed_at', 'error_message', 'generation_time_seconds'
        ])

    def increment_download_count(self):
        """Increment the download counter."""
        self.download_count = models.F('download_count') + 1
        self.save(update_fields=['download_count'])


class DashboardConfiguration(models.Model):
    """
    Model to store user-specific dashboard configurations and preferences.
    """

    DASHBOARD_TYPES = [
        ('executive', 'Executive Dashboard'),
        ('operational', 'Operational Dashboard'),
        ('compliance', 'Compliance Dashboard'),
        ('risk', 'Risk Dashboard'),
        ('vendor', 'Vendor Dashboard'),
        ('policy', 'Policy Dashboard'),
        ('training', 'Training Dashboard'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dashboard_configs')
    dashboard_type = models.CharField(max_length=50, choices=DASHBOARD_TYPES)

    # Configuration data
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)

    # Layout and display preferences
    layout_config = models.JSONField(default=dict, blank=True)  # Widget positions, sizes
    filters = models.JSONField(default=dict, blank=True)  # Default filters
    refresh_interval = models.PositiveIntegerField(default=300)  # Seconds

    # Sharing settings
    is_shared = models.BooleanField(default=False)
    shared_with_users = models.ManyToManyField(
        User, blank=True, related_name='shared_dashboard_configs'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dashboard_configurations'
        ordering = ['-created_at']
        unique_together = [['user', 'dashboard_type', 'name']]
        indexes = [
            models.Index(fields=['user', 'dashboard_type']),
            models.Index(fields=['is_shared']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_dashboard_type_display()}) - {self.user.username}"


class AnalyticsMetric(models.Model):
    """
    Model to store calculated analytics metrics for caching and historical tracking.
    """

    METRIC_CATEGORIES = [
        ('risk', 'Risk Management'),
        ('compliance', 'Compliance'),
        ('vendor', 'Vendor Management'),
        ('policy', 'Policy Management'),
        ('training', 'Training & Awareness'),
        ('integrated', 'Integrated Analysis'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(max_length=50, choices=METRIC_CATEGORIES)
    metric_name = models.CharField(max_length=255)
    metric_key = models.CharField(max_length=100)  # Unique identifier for the metric

    # Metric data
    value = models.JSONField()  # Store the calculated metric value
    calculation_date = models.DateTimeField(default=timezone.now)
    data_source = models.CharField(max_length=255)  # Source of the data

    # Metadata
    calculation_time_ms = models.PositiveIntegerField(null=True, blank=True)
    data_freshness = models.DateTimeField(null=True, blank=True)  # When underlying data was last updated
    is_cached = models.BooleanField(default=True)
    cache_expires_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'analytics_metrics'
        ordering = ['-calculation_date']
        unique_together = [['metric_key', 'calculation_date']]
        indexes = [
            models.Index(fields=['category', 'metric_key']),
            models.Index(fields=['calculation_date']),
            models.Index(fields=['cache_expires_at']),
        ]

    def __str__(self):
        return f"{self.metric_name} - {self.calculation_date.strftime('%Y-%m-%d %H:%M')}"

    @property
    def is_cache_valid(self):
        """Check if the cached metric is still valid."""
        if self.cache_expires_at:
            return timezone.now() < self.cache_expires_at
        return False


class ReportTemplate(models.Model):
    """
    Model to store reusable report templates for analytics exports.
    """

    TEMPLATE_TYPES = [
        ('executive', 'Executive Report'),
        ('compliance', 'Compliance Report'),
        ('risk', 'Risk Assessment Report'),
        ('vendor', 'Vendor Risk Report'),
        ('audit', 'Audit Report'),
        ('custom', 'Custom Report'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES)

    # Template configuration
    sections = models.JSONField(default=list)  # Report sections and their configuration
    default_filters = models.JSONField(default=dict)  # Default filter values
    styling_config = models.JSONField(default=dict)  # Colors, fonts, logos, etc.

    # Access control
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='report_templates')
    is_public = models.BooleanField(default=False)
    allowed_users = models.ManyToManyField(User, blank=True, related_name='accessible_templates')

    # Usage tracking
    usage_count = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'report_templates'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['template_type']),
            models.Index(fields=['is_public']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"

    def increment_usage(self):
        """Increment the usage counter and update last used timestamp."""
        self.usage_count = models.F('usage_count') + 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['usage_count', 'last_used_at'])