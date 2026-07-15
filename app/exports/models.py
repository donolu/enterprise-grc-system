from django.db import models
from django.contrib.auth import get_user_model
from catalogs.models import ControlAssessment, Framework

User = get_user_model()


class AssessmentReport(models.Model):
    """
    Track assessment report generation requests and their status.
    """
    REPORT_TYPES = [
        ('assessment_summary', 'Assessment Summary Report'),
        ('detailed_assessment', 'Detailed Assessment Report'),
        ('evidence_portfolio', 'Evidence Portfolio Report'),
        ('compliance_gap', 'Compliance Gap Analysis'),
        ('risk_analytics', 'Risk Analytics & Integration Report'),
    ]
    
    REPORT_STATUS = [
        ('pending', 'Pending Generation'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    # Report metadata
    report_type = models.CharField(max_length=30, choices=REPORT_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Report scope
    framework = models.ForeignKey(
        Framework, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="Framework to generate report for (if applicable)"
    )
    assessments = models.ManyToManyField(
        ControlAssessment,
        blank=True,
        help_text="Specific assessments to include (if applicable)"
    )
    
    # Report generation
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE)
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=15, choices=REPORT_STATUS, default='pending')
    
    # Report output
    generated_file = models.ForeignKey(
        'core.Document',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Generated PDF report file"
    )
    generation_started_at = models.DateTimeField(null=True, blank=True)
    generation_completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Report configuration
    include_evidence_summary = models.BooleanField(default=True)
    include_implementation_notes = models.BooleanField(default=True)
    include_overdue_items = models.BooleanField(default=True)
    include_charts = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['requested_by', '-requested_at']),
            models.Index(fields=['status']),
            models.Index(fields=['report_type']),
        ]
    
    def __str__(self):
        return f"{self.get_report_type_display()} - {self.title}"


class TenantDataExport(models.Model):
    """
    Track full tenant data export requests across GRC modules.
    """

    EXPORT_FORMATS = [
        ('xlsx', 'Excel workbook'),
        ('csv_zip', 'CSV archive'),
    ]

    EXPORT_STATUS = [
        ('pending', 'Pending Generation'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    title = models.CharField(max_length=200, default='Tenant data export')
    export_format = models.CharField(max_length=20, choices=EXPORT_FORMATS, default='xlsx')
    selected_modules = models.JSONField(default=list, blank=True)

    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tenant_data_exports')
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=15, choices=EXPORT_STATUS, default='pending')

    generated_file = models.ForeignKey(
        'core.Document',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Generated spreadsheet or CSV archive',
    )
    generation_started_at = models.DateTimeField(null=True, blank=True)
    generation_completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    record_counts = models.JSONField(default=dict, blank=True)
    coverage_manifest = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['requested_by', '-requested_at']),
            models.Index(fields=['status']),
            models.Index(fields=['export_format']),
        ]

    def __str__(self):
        return f'{self.title} ({self.export_format})'
