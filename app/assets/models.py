from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class Asset(models.Model):
    """
    Information asset held by a tenant.
    """
    ASSET_TYPES = [
        ('server', 'Server'),
        ('workstation', 'Workstation'),
        ('monitor', 'Monitor'),
        ('mobile_device', 'Mobile Device'),
        ('printer', 'Printer'),
        ('infrastructure', 'Infrastructure'),
        ('application', 'Application'),
        ('database', 'Database'),
        ('document', 'Document'),
        ('other', 'Other'),
    ]

    CLASSIFICATION_CHOICES = [
        ('public', 'Public'),
        ('internal', 'Internal'),
        ('confidential', 'Confidential'),
        ('restricted', 'Restricted'),
    ]

    CRITICALITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    LIFECYCLE_STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('active', 'Active'),
        ('maintenance', 'Maintenance'),
        ('retired', 'Retired'),
        ('disposed', 'Disposed'),
    ]

    asset_id = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=255)
    asset_type = models.CharField(max_length=30, choices=ASSET_TYPES, default='other')
    description = models.TextField(blank=True)

    classification = models.CharField(
        max_length=30,
        choices=CLASSIFICATION_CHOICES,
        default='internal',
    )
    criticality = models.CharField(
        max_length=20,
        choices=CRITICALITY_CHOICES,
        default='medium',
    )
    lifecycle_status = models.CharField(
        max_length=30,
        choices=LIFECYCLE_STATUS_CHOICES,
        default='active',
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_assets',
    )
    owner_name = models.CharField(max_length=255, blank=True)
    custodian = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)

    domain = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    mac_address = models.CharField(max_length=64, blank=True)
    serial_number = models.CharField(max_length=128, blank=True)
    manufacturer = models.CharField(max_length=255, blank=True)
    model = models.CharField(max_length=255, blank=True)
    operating_system = models.CharField(max_length=255, blank=True)
    version = models.CharField(max_length=100, blank=True)

    acquisition_date = models.DateField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)
    next_review_date = models.DateField(null=True, blank=True)
    disposal_date = models.DateField(null=True, blank=True)

    linked_risks = models.ManyToManyField(
        'risk.Risk',
        blank=True,
        related_name='linked_assets',
    )
    linked_controls = models.ManyToManyField(
        'catalogs.Control',
        blank=True,
        related_name='linked_assets',
    )
    linked_documents = models.ManyToManyField(
        'core.Document',
        blank=True,
        related_name='linked_assets',
    )

    source_path = models.CharField(max_length=500, blank=True)
    source_sheet = models.CharField(max_length=120, blank=True)
    source_row = models.PositiveIntegerField(null=True, blank=True)
    source_checksum = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_assets',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['asset_id', 'name']
        indexes = [
            models.Index(fields=['asset_type', 'lifecycle_status']),
            models.Index(fields=['criticality']),
            models.Index(fields=['classification']),
            models.Index(fields=['owner']),
            models.Index(fields=['next_review_date']),
            models.Index(fields=['source_checksum']),
        ]

    def __str__(self):
        return f'{self.asset_id}: {self.name}'

    @property
    def is_review_overdue(self):
        return bool(self.next_review_date and self.next_review_date < timezone.now().date())

    @property
    def days_until_review(self):
        if not self.next_review_date:
            return None
        return (self.next_review_date - timezone.now().date()).days


class AssetReviewReminderLog(models.Model):
    REMINDER_TYPES = [
        ('advance_warning', 'Advance Warning'),
        ('due_today', 'Due Today'),
        ('overdue', 'Overdue'),
    ]

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='review_reminder_logs',
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='asset_review_reminder_logs',
    )
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPES)
    review_date = models.DateField()
    sent_at = models.DateTimeField(auto_now_add=True)
    email_sent = models.BooleanField(default=False)

    class Meta:
        unique_together = [('asset', 'owner', 'reminder_type', 'review_date')]
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['asset', 'owner']),
            models.Index(fields=['review_date', 'reminder_type']),
        ]

    def __str__(self):
        return f'{self.reminder_type} reminder for {self.asset.asset_id}'
