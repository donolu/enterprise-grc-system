from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django_tenants.models import TenantMixin, DomainMixin

class Tenant(TenantMixin):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Billing information
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    current_plan = models.CharField(max_length=20, default='free', choices=[
        ('free', 'Free'),
        ('basic', 'Basic'), 
        ('enterprise', 'Enterprise')
    ])
    
    def __str__(self):
        return f"{self.name} ({self.schema_name})"

class Domain(DomainMixin):
    pass

class User(AbstractUser):
    # In django-tenants, users are isolated by schema, not by FK
    pass

class Plan(models.Model):
    """
    Subscription plans with pricing and feature limits.
    Stored in public schema for all tenants to reference.
    """
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stripe_price_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Feature limits
    max_users = models.PositiveIntegerField(default=5)
    max_documents = models.PositiveIntegerField(default=100)
    max_frameworks = models.PositiveIntegerField(default=1)
    has_api_access = models.BooleanField(default=False)
    has_advanced_reporting = models.BooleanField(default=False)
    has_priority_support = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['price_monthly']
    
    def __str__(self):
        return f"{self.name} (${self.price_monthly}/month)"


class Subscription(models.Model):
    """
    Tenant subscription details linked to Stripe.
    Stored in public schema to maintain billing across all tenants.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('unpaid', 'Unpaid'),
        ('trialing', 'Trialing'),
        ('incomplete', 'Incomplete'),
    ]
    
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    
    # Stripe integration
    stripe_subscription_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Subscription details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    trial_start = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    
    # Grandfathering and customization
    custom_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_grandfathered = models.BooleanField(default=False)
    seats_included = models.PositiveIntegerField(default=5)
    
    # Custom limit overrides (null = use plan default)
    custom_max_users = models.PositiveIntegerField(null=True, blank=True, help_text="Override plan's max users limit")
    custom_max_documents = models.PositiveIntegerField(null=True, blank=True, help_text="Override plan's max documents limit")
    custom_max_frameworks = models.PositiveIntegerField(null=True, blank=True, help_text="Override plan's max frameworks limit")
    custom_max_storage_gb = models.PositiveIntegerField(null=True, blank=True, help_text="Override plan's max storage limit")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.tenant.name} - {self.plan.name} ({self.status})"
    
    @property
    def is_active(self):
        return self.status in ['active', 'trialing']
    
    @property
    def effective_price(self):
        """Return custom price if grandfathered, otherwise plan price"""
        return self.custom_price if self.custom_price else self.plan.price_monthly
    
    def get_effective_user_limit(self):
        """Return custom user limit if set, otherwise plan limit"""
        return self.custom_max_users if self.custom_max_users is not None else self.plan.max_users
    
    def get_effective_document_limit(self):
        """Return custom document limit if set, otherwise plan limit"""
        return self.custom_max_documents if self.custom_max_documents is not None else self.plan.max_documents
    
    def get_effective_framework_limit(self):
        """Return custom framework limit if set, otherwise plan limit"""
        return self.custom_max_frameworks if self.custom_max_frameworks is not None else self.plan.max_frameworks
    
    def get_effective_storage_limit(self):
        """Return custom storage limit if set, otherwise plan limit (default 1GB)"""
        plan_storage = getattr(self.plan, 'max_storage_gb', 1)  # Default 1GB if not set
        return self.custom_max_storage_gb if self.custom_max_storage_gb is not None else plan_storage


class BillingEvent(models.Model):
    """
    Track billing-related events from Stripe webhooks.
    Stored in public schema for system-wide billing audit.
    """
    EVENT_TYPES = [
        ('invoice.payment_succeeded', 'Invoice Payment Succeeded'),
        ('invoice.payment_failed', 'Invoice Payment Failed'),
        ('customer.subscription.created', 'Subscription Created'),
        ('customer.subscription.updated', 'Subscription Updated'),
        ('customer.subscription.deleted', 'Subscription Deleted'),
        ('checkout.session.completed', 'Checkout Completed'),
    ]
    
    stripe_event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, null=True, blank=True)
    
    # Event data
    data = models.JSONField(default=dict)
    processed = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['stripe_event_id']),
            models.Index(fields=['event_type', '-created_at']),
            models.Index(fields=['processed']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.stripe_event_id}"


class LimitOverrideRequest(models.Model):
    """
    Request system for overriding subscription limits with approval workflow.
    Stored in public schema for cross-tenant limit management.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('applied', 'Applied'),
        ('expired', 'Expired'),
    ]
    
    LIMIT_TYPES = [
        ('max_users', 'Maximum Users'),
        ('max_documents', 'Maximum Documents'), 
        ('max_frameworks', 'Maximum Frameworks'),
        ('max_storage_gb', 'Maximum Storage (GB)'),
    ]
    
    URGENCY_CHOICES = [
        ('low', 'Low - Standard Review'),
        ('medium', 'Medium - 24 Hour Review'),
        ('high', 'High - Same Day Review'),
        ('critical', 'Critical - Immediate Review'),
    ]
    
    # Request details
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='limit_override_requests')
    limit_type = models.CharField(max_length=20, choices=LIMIT_TYPES)
    current_limit = models.PositiveIntegerField()
    requested_limit = models.PositiveIntegerField()
    
    # Business justification
    business_justification = models.TextField(help_text="Explain why this limit increase is needed")
    urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES, default='low')
    temporary = models.BooleanField(default=False, help_text="Is this a temporary increase?")
    expires_at = models.DateTimeField(null=True, blank=True, help_text="When should temporary limits expire?")
    
    # Request lifecycle
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    requested_by = models.CharField(max_length=255, help_text="User who requested the override")
    requested_at = models.DateTimeField(auto_now_add=True)
    
    # Approval tracking
    first_approver = models.CharField(max_length=255, blank=True, null=True)
    first_approved_at = models.DateTimeField(null=True, blank=True)
    first_approval_notes = models.TextField(blank=True)
    
    second_approver = models.CharField(max_length=255, blank=True, null=True)
    second_approved_at = models.DateTimeField(null=True, blank=True)
    second_approval_notes = models.TextField(blank=True)
    
    # Final decision
    final_decision_by = models.CharField(max_length=255, blank=True, null=True)
    final_decision_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Application tracking
    applied_at = models.DateTimeField(null=True, blank=True)
    applied_by = models.CharField(max_length=255, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['subscription', 'status']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['urgency', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.subscription.tenant.name} - {self.get_limit_type_display()} Override ({self.status})"
    
    @property
    def is_pending(self):
        return self.status == 'pending'
    
    @property
    def needs_first_approval(self):
        return self.status == 'pending' and not self.first_approved_at
    
    @property
    def needs_second_approval(self):
        return self.status == 'pending' and self.first_approved_at and not self.second_approved_at
    
    @property
    def is_fully_approved(self):
        return self.first_approved_at and self.second_approved_at and self.status == 'approved'
    
    @property
    def can_be_applied(self):
        return self.is_fully_approved and self.status != 'applied'
    
    def approve_first(self, approver_name, notes=""):
        """Record first approval."""
        if self.needs_first_approval:
            self.first_approver = approver_name
            self.first_approved_at = timezone.now()
            self.first_approval_notes = notes
            self.save()
            return True
        return False
    
    def approve_second(self, approver_name, notes=""):
        """Record second approval and mark as approved."""
        if self.needs_second_approval:
            self.second_approver = approver_name
            self.second_approved_at = timezone.now()
            self.second_approval_notes = notes
            self.status = 'approved'
            self.final_decision_by = approver_name
            self.final_decision_at = timezone.now()
            self.save()
            return True
        return False
    
    def reject(self, rejector_name, reason):
        """Reject the override request."""
        self.status = 'rejected'
        self.rejection_reason = reason
        self.final_decision_by = rejector_name
        self.final_decision_at = timezone.now()
        self.save()
        return True
    
    def apply_override(self, applied_by_name):
        """Apply the approved override to the subscription."""
        if not self.can_be_applied:
            return False
        
        # Update the subscription with custom limits
        subscription = self.subscription
        if self.limit_type == 'max_users':
            subscription.custom_max_users = self.requested_limit
        elif self.limit_type == 'max_documents':
            subscription.custom_max_documents = self.requested_limit
        elif self.limit_type == 'max_frameworks':
            subscription.custom_max_frameworks = self.requested_limit
        elif self.limit_type == 'max_storage_gb':
            subscription.custom_max_storage_gb = self.requested_limit
        
        subscription.save()
        
        # Mark override as applied
        self.status = 'applied'
        self.applied_at = timezone.now()
        self.applied_by = applied_by_name
        self.save()
        
        # Create audit log
        AuditEvent.objects.create(
            event="LIMIT_OVERRIDE_APPLIED",
            details={
                'limit_type': self.limit_type,
                'previous_limit': self.current_limit,
                'new_limit': self.requested_limit,
                'override_request_id': self.id,
                'applied_by': applied_by_name
            }
        )
        
        return True

class AuditEvent(models.Model):
    # These are tenant-specific - no need for tenant FK since isolated by schema
    user = models.ForeignKey("core.User", on_delete=models.SET_NULL, null=True)
    event = models.CharField(max_length=120)
    details = models.JSONField(default=dict, blank=True)
    at = models.DateTimeField(default=timezone.now)


def tenant_file_upload_path(instance, filename):
    """
    Generate file upload path with tenant isolation.
    Files are organized by model type and date.
    """
    date_path = timezone.now().strftime('%Y/%m/%d')
    model_name = instance.__class__.__name__.lower()
    return f"{model_name}/{date_path}/{filename}"


class Document(models.Model):
    """
    Document model for file uploads.
    Demonstrates Azure Blob Storage integration with tenant isolation.
    """
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(
        upload_to=tenant_file_upload_path,
        help_text="Upload documents (PDF, DOC, XLS, etc.)"
    )
    
    # Metadata
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_documents')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # File metadata
    file_size = models.PositiveIntegerField(null=True, blank=True, help_text="File size in bytes")
    mime_type = models.CharField(max_length=100, blank=True)
    
    # Access control
    is_public = models.BooleanField(default=False, help_text="Whether file can be accessed without authentication")
    
    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['uploaded_by', '-uploaded_at']),
            models.Index(fields=['is_public']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        # Set file metadata when saving
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)
    
    @property
    def file_url(self):
        """Get the URL for the uploaded file."""
        if self.file:
            return self.file.url
        return None
    
    @property
    def file_name(self):
        """Get the original filename."""
        if self.file:
            return self.file.name.split('/')[-1]
        return None


class DocumentAccess(models.Model):
    """
    Track document access for audit purposes.
    """
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='access_logs')
    accessed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    accessed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-accessed_at']
        indexes = [
            models.Index(fields=['document', '-accessed_at']),
            models.Index(fields=['accessed_by', '-accessed_at']),
        ]
    
    def __str__(self):
        return f"{self.accessed_by.username} accessed {self.document.title}"
