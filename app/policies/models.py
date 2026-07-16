"""
Policy Repository Models

Comprehensive policy management system supporting policy versioning,
document storage, and acknowledgment tracking for compliance requirements.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from django.urls import reverse
import uuid
import os

User = get_user_model()


def policy_upload_path(instance, filename):
    """Generate upload path for policy documents."""
    # Create path: policies/{policy_id}/{version}/{filename}
    return f'policies/{instance.policy.id}/{instance.version_number}/{filename}'


def policy_final_pdf_upload_path(instance, filename):
    """Generate upload path for final policy PDFs."""
    return f'policies/{instance.policy.id}/{instance.version_number}/final/{filename}'


class PolicyCategory(models.Model):
    """
    Categories for organizing policies (e.g., HR, Security, IT, Legal).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Category name (e.g., Security, HR, Legal, IT)"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of this policy category"
    )
    color = models.CharField(
        max_length=7,
        default="#6366f1",
        help_text="Hex color code for visual identification"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Policy Category"
        verbose_name_plural = "Policy Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Policy(models.Model):
    """
    Main policy entity that can have multiple versions.
    """

    APPROVAL_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('archived', 'Archived'),
    ]

    POLICY_TYPE_CHOICES = [
        ('procedure', 'Procedure'),
        ('policy', 'Policy'),
        ('standard', 'Standard'),
        ('guideline', 'Guideline'),
        ('framework', 'Framework'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy_code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique policy code (e.g., POL-SEC-001)"
    )
    title = models.CharField(
        max_length=200,
        help_text="Policy title"
    )
    category = models.ForeignKey(
        PolicyCategory,
        on_delete=models.PROTECT,
        related_name='policies'
    )
    policy_type = models.CharField(
        max_length=20,
        choices=POLICY_TYPE_CHOICES,
        default='policy'
    )
    status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default='draft'
    )

    # Policy management
    owner = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='owned_policies',
        help_text="Policy owner/manager responsible for this policy"
    )
    approver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_policies',
        help_text="User who approved this policy"
    )

    # Review schedule
    review_frequency_months = models.PositiveIntegerField(
        default=12,
        help_text="How often this policy should be reviewed (in months)"
    )
    next_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="When this policy is due for review"
    )

    # Acknowledgment requirements
    requires_acknowledgment = models.BooleanField(
        default=True,
        help_text="Whether users must acknowledge reading this policy"
    )
    acknowledgment_validity_days = models.PositiveIntegerField(
        default=365,
        help_text="How long acknowledgments remain valid (days)"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_policies'
    )

    class Meta:
        verbose_name = "Policy"
        verbose_name_plural = "Policies"
        ordering = ['policy_code', 'title']

    def __str__(self):
        return f"{self.policy_code} - {self.title}"

    @property
    def current_version(self):
        """Get the current active version of this policy."""
        return self.versions.filter(is_active=True).first()

    @property
    def latest_version(self):
        """Get the latest version regardless of active status."""
        return self.versions.order_by('-version_number').first()

    @property
    def is_due_for_review(self):
        """Check if policy is due for review."""
        if not self.next_review_date:
            return False
        return self.next_review_date <= timezone.now().date()

    def get_absolute_url(self):
        return reverse('admin:policies_policy_change', args=[self.pk])

    def save(self, *args, **kwargs):
        # Auto-generate policy code if not provided
        if not self.policy_code:
            category_prefix = self.category.name[:3].upper()
            count = Policy.objects.filter(category=self.category).count() + 1
            self.policy_code = f"POL-{category_prefix}-{count:03d}"

        # Set next review date if not provided
        if not self.next_review_date and self.review_frequency_months:
            from dateutil.relativedelta import relativedelta  # type: ignore[import-untyped]
            self.next_review_date = timezone.now().date() + relativedelta(months=self.review_frequency_months)

        super().save(*args, **kwargs)


class PolicyVersion(models.Model):
    """
    Versioned policy documents with file storage support.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    LIFECYCLE_CHOICES = [
        ('template', 'Template'),
        ('draft', 'Draft'),
        ('client_modified', 'Client Modified'),
        ('approved', 'Approved'),
        ('final', 'Final'),
    ]

    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    version_number = models.CharField(
        max_length=10,
        help_text="Version number (e.g., 1.0, 1.1, 2.0)"
    )

    # Document storage
    document = models.FileField(
        upload_to=policy_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'docx', 'doc'])],
        help_text="Policy document (PDF, DOCX, or DOC)"
    )
    document_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Document size in bytes"
    )
    final_pdf = models.FileField(
        upload_to=policy_final_pdf_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        null=True,
        blank=True,
        help_text="Final PDF generated from the approved editable source"
    )
    final_pdf_size = models.PositiveIntegerField(null=True, blank=True)

    # Version metadata
    summary = models.TextField(
        blank=True,
        help_text="Summary of changes in this version"
    )
    lifecycle_state = models.CharField(
        max_length=30,
        choices=LIFECYCLE_CHOICES,
        default='draft',
        help_text="Document lifecycle state from template through final PDF"
    )
    is_active = models.BooleanField(
        default=False,
        help_text="Whether this is the current active version"
    )
    is_published = models.BooleanField(
        default=False,
        help_text="Whether this version is published and available to users"
    )

    # Approval workflow
    approved_at = models.DateTimeField(
        null=True,
        blank=True
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_policy_versions'
    )
    finalized_at = models.DateTimeField(null=True, blank=True)
    finalized_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='finalized_policy_versions'
    )

    # Effective dates
    effective_date = models.DateField(
        default=timezone.now,
        help_text="When this version becomes effective"
    )
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text="When this version expires (optional)"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_policy_versions'
    )

    class Meta:
        verbose_name = "Policy Version"
        verbose_name_plural = "Policy Versions"
        ordering = ['-version_number']
        unique_together = ['policy', 'version_number']

    def __str__(self):
        return f"{self.policy.policy_code} v{self.version_number}"

    @property
    def file_name(self):
        """Get the original filename."""
        if self.document:
            return os.path.basename(self.document.name)
        return None

    @property
    def file_extension(self):
        """Get the file extension."""
        if self.document:
            return os.path.splitext(self.document.name)[1].lower()
        return None

    @property
    def is_current(self):
        """Check if this is the current active version."""
        return self.is_active and self.policy.current_version == self

    @property
    def is_expired(self):
        """Check if this version has expired."""
        if not self.expiry_date:
            return False
        return self.expiry_date < timezone.now().date()

    def save(self, *args, **kwargs):
        # Set document size
        if self.document:
            self.document_size = self.document.size
        if self.final_pdf:
            self.final_pdf_size = self.final_pdf.size

        # Ensure only one active version per policy
        if self.is_active:
            PolicyVersion.objects.filter(
                policy=self.policy,
                is_active=True
            ).exclude(pk=self.pk).update(is_active=False)

        super().save(*args, **kwargs)


class PolicyVersionAuditLog(models.Model):
    ACTION_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('edited', 'Edited'),
        ('published', 'Published'),
        ('activated', 'Activated'),
        ('approved', 'Approved'),
        ('finalized', 'Finalized'),
        ('conversion_failed', 'Conversion Failed'),
        ('distributed', 'Distributed'),
        ('acknowledged', 'Acknowledged'),
        ('downloaded_pdf', 'Downloaded PDF'),
        ('downloaded_source', 'Downloaded Source'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy_version = models.ForeignKey(
        PolicyVersion,
        on_delete=models.CASCADE,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=40, choices=ACTION_CHOICES)
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='policy_version_audit_logs'
    )
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['policy_version', '-created_at']),
            models.Index(fields=['action', '-created_at']),
        ]

    def __str__(self):
        return f'{self.action} for {self.policy_version}'


class PolicyAcknowledgment(models.Model):
    """
    Track user acknowledgments of policy versions.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='policy_acknowledgments'
    )
    policy_version = models.ForeignKey(
        PolicyVersion,
        on_delete=models.CASCADE,
        related_name='acknowledgments'
    )

    # Acknowledgment details
    acknowledged_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address when acknowledgment was made"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="Browser user agent string"
    )

    # Validity
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this acknowledgment expires"
    )

    class Meta:
        verbose_name = "Policy Acknowledgment"
        verbose_name_plural = "Policy Acknowledgments"
        ordering = ['-acknowledged_at']
        unique_together = ['user', 'policy_version']

    def __str__(self):
        return f"{self.user.email} acknowledged {self.policy_version}"

    @property
    def is_expired(self):
        """Check if acknowledgment has expired."""
        if not self.expires_at:
            return False
        return self.expires_at < timezone.now()

    @property
    def is_valid(self):
        """Check if acknowledgment is still valid."""
        return not self.is_expired

    def save(self, *args, **kwargs):
        # Set expiry date based on policy settings
        if not self.expires_at and self.policy_version.policy.acknowledgment_validity_days:
            from datetime import timedelta
            self.expires_at = timezone.now() + timedelta(
                days=self.policy_version.policy.acknowledgment_validity_days
            )

        super().save(*args, **kwargs)


class PolicyDistribution(models.Model):
    """
    Track policy distribution to users and groups.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy_version = models.ForeignKey(
        PolicyVersion,
        on_delete=models.CASCADE,
        related_name='distributions'
    )

    # Distribution details
    distributed_to = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_policies'
    )
    distributed_at = models.DateTimeField(auto_now_add=True)
    distributed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='distributed_policies'
    )

    # Notification tracking
    notification_sent = models.BooleanField(default=False)
    notification_sent_at = models.DateTimeField(null=True, blank=True)

    # Reminder tracking
    reminder_count = models.PositiveIntegerField(default=0)
    last_reminder_sent = models.DateTimeField(null=True, blank=True)

    # Status
    acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Policy Distribution"
        verbose_name_plural = "Policy Distributions"
        ordering = ['-distributed_at']
        unique_together = ['policy_version', 'distributed_to']

    def __str__(self):
        return f"{self.policy_version} → {self.distributed_to.email}"

    @property
    def is_overdue(self):
        """Check if acknowledgment is overdue."""
        if self.acknowledged or not self.distributed_at:
            return False
        # Consider overdue after 30 days without acknowledgment
        from datetime import timedelta
        overdue_date = self.distributed_at + timedelta(days=30)
        return timezone.now() > overdue_date
