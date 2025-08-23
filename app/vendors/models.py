"""
Vendor Management Models

Comprehensive vendor profile and relationship management system
supporting vendor risk assessment, contact management, and contract tracking.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import EmailValidator, RegexValidator
from django.utils import timezone
from decimal import Decimal
import uuid
from datetime import timedelta

User = get_user_model()


class RegionalConfig(models.Model):
    """
    Configuration for region-specific vendor due diligence requirements.
    Allows customization of required fields, compliance standards, and validation rules.
    """
    
    # Regional Information
    region_code = models.CharField(
        max_length=10,
        unique=True,
        validators=[RegexValidator(regex=r'^[A-Z]{2,10}$', message='Enter a valid region code (e.g., US, EU, APAC)')],
        help_text="Region code (e.g., US, EU, APAC, CA, UK)"
    )
    region_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Required Fields Configuration
    required_fields = models.JSONField(
        default=dict,
        help_text="JSON configuration defining which standard fields are required in this region"
    )
    
    # Custom Fields Configuration
    custom_fields = models.JSONField(
        default=list,
        help_text="JSON array defining additional custom fields required for this region"
    )
    
    # Compliance Requirements
    compliance_standards = models.JSONField(
        default=list,
        help_text="List of compliance standards applicable to this region"
    )
    
    # Validation Rules
    validation_rules = models.JSONField(
        default=dict,
        help_text="Custom validation rules for fields in this region"
    )
    
    # Data Processing Requirements
    data_processing_requirements = models.JSONField(
        default=dict,
        help_text="Specific data processing and privacy requirements"
    )
    
    # Contract Requirements
    contract_requirements = models.JSONField(
        default=dict,
        help_text="Region-specific contract terms and requirements"
    )
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['region_code']
        indexes = [
            models.Index(fields=['region_code']),
            models.Index(fields=['is_active']),
        ]
        verbose_name = 'Regional Configuration'
        verbose_name_plural = 'Regional Configurations'
    
    def __str__(self):
        return f"{self.region_code} - {self.region_name}"


class VendorCategory(models.Model):
    """
    Categorization system for vendors (e.g., IT Services, Cloud Provider, 
    Legal Services, Financial Services, etc.)
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color_code = models.CharField(
        max_length=7,
        default='#6c757d',
        validators=[RegexValidator(regex=r'^#[0-9A-Fa-f]{6}$', message='Enter a valid hex color code')],
        help_text="Hex color code for visual identification (e.g., #0066cc)"
    )
    risk_weight = models.CharField(
        max_length=10,
        choices=[
            ('low', 'Low Risk'),
            ('medium', 'Medium Risk'),
            ('high', 'High Risk'),
            ('critical', 'Critical Risk'),
        ],
        default='medium',
        help_text="Default risk level for vendors in this category"
    )
    compliance_requirements = models.JSONField(
        default=dict,
        blank=True,
        help_text="Category-specific compliance requirements and standards"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Vendor Categories'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['risk_weight']),
        ]
    
    def __str__(self):
        return self.name


class Vendor(models.Model):
    """
    Core vendor profile model with comprehensive vendor information
    including contact details, services, contracts, and risk assessment.
    """
    # Basic Information
    vendor_id = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique vendor identifier (auto-generated: VEN-YYYY-NNNN)"
    )
    name = models.CharField(max_length=200)
    legal_name = models.CharField(
        max_length=200, 
        blank=True,
        help_text="Official legal business name if different from common name"
    )
    category = models.ForeignKey(
        VendorCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Primary vendor category for classification"
    )
    
    # Business Details
    business_description = models.TextField(
        blank=True,
        help_text="Description of vendor's business and services provided"
    )
    website = models.URLField(blank=True)
    tax_id = models.CharField(
        max_length=50,
        blank=True,
        help_text="Tax ID, EIN, or equivalent business identifier"
    )
    duns_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="D-U-N-S Number for business identification"
    )
    
    # Address Information
    address_line1 = models.CharField(max_length=200, blank=True)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state_province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Status and Classification
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='under_review'
    )
    
    VENDOR_TYPE_CHOICES = [
        ('supplier', 'Supplier'),
        ('service_provider', 'Service Provider'),
        ('consultant', 'Consultant'),
        ('contractor', 'Contractor'),
        ('partner', 'Strategic Partner'),
        ('subcontractor', 'Subcontractor'),
    ]
    vendor_type = models.CharField(
        max_length=20,
        choices=VENDOR_TYPE_CHOICES,
        default='supplier'
    )
    
    # Risk Assessment
    RISK_LEVEL_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    risk_level = models.CharField(
        max_length=10,
        choices=RISK_LEVEL_CHOICES,
        default='medium'
    )
    risk_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Calculated risk score (0-100)"
    )
    
    # Financial Information
    annual_spend = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Annual spend with this vendor"
    )
    credit_rating = models.CharField(max_length=10, blank=True)
    payment_terms = models.CharField(
        max_length=50,
        blank=True,
        help_text="Standard payment terms (e.g., Net 30, Net 60)"
    )
    
    # Regional Configuration  
    operating_regions = models.JSONField(
        default=list,
        blank=True,
        help_text="List of regions where this vendor operates (e.g., ['US', 'EU', 'APAC'])"
    )
    primary_region = models.CharField(
        max_length=10,
        blank=True,
        help_text="Primary operating region code for due diligence requirements"
    )
    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Region-specific custom fields and their values"
    )
    
    # Compliance and Certifications
    certifications = models.JSONField(
        default=list,
        blank=True,
        help_text="List of relevant certifications (ISO, SOC, etc.)"
    )
    compliance_status = models.JSONField(
        default=dict,
        blank=True,
        help_text="Compliance status for various requirements"
    )
    data_processing_agreement = models.BooleanField(
        default=False,
        help_text="Data Processing Agreement in place"
    )
    security_assessment_completed = models.BooleanField(
        default=False,
        help_text="Security assessment completed"
    )
    security_assessment_date = models.DateField(null=True, blank=True)
    
    # Relationship Management
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_vendors',
        help_text="Primary relationship manager for this vendor"
    )
    relationship_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date relationship with vendor began"
    )
    
    # Contract Information
    primary_contract_number = models.CharField(max_length=100, blank=True)
    contract_start_date = models.DateField(null=True, blank=True)
    contract_end_date = models.DateField(null=True, blank=True)
    auto_renewal = models.BooleanField(
        default=False,
        help_text="Contract has automatic renewal clause"
    )
    renewal_notice_days = models.IntegerField(
        default=90,
        help_text="Days notice required for contract renewal/termination"
    )
    
    # Performance Metrics
    performance_score = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Overall performance score (0-100)"
    )
    last_performance_review = models.DateField(null=True, blank=True)
    
    # Notes and Additional Information
    notes = models.TextField(
        blank=True,
        help_text="Additional notes and comments about the vendor"
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Tags for categorization and filtering"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_vendors'
    )
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['vendor_id']),
            models.Index(fields=['name']),
            models.Index(fields=['status']),
            models.Index(fields=['risk_level']),
            models.Index(fields=['category']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['contract_end_date']),
            models.Index(fields=['created_at']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.vendor_id:
            self.vendor_id = self._generate_vendor_id()
        super().save(*args, **kwargs)
    
    def _generate_vendor_id(self):
        """Generate unique vendor ID in format VEN-YYYY-NNNN"""
        year = timezone.now().year
        last_vendor = Vendor.objects.filter(
            vendor_id__startswith=f'VEN-{year}-'
        ).order_by('vendor_id').last()
        
        if last_vendor:
            last_number = int(last_vendor.vendor_id.split('-')[-1])
            next_number = last_number + 1
        else:
            next_number = 1
            
        return f'VEN-{year}-{next_number:04d}'
    
    @property
    def full_address(self):
        """Get formatted full address"""
        address_parts = [
            self.address_line1,
            self.address_line2,
            self.city,
            self.state_province,
            self.postal_code,
            self.country
        ]
        return ', '.join([part for part in address_parts if part])
    
    @property
    def is_contract_expiring_soon(self):
        """Check if contract is expiring within renewal notice period"""
        if not self.contract_end_date:
            return False
        
        days_until_expiry = (self.contract_end_date - timezone.now().date()).days
        return days_until_expiry <= self.renewal_notice_days
    
    @property
    def days_until_contract_expiry(self):
        """Get days until contract expiry"""
        if not self.contract_end_date:
            return None
        return (self.contract_end_date - timezone.now().date()).days
    
    def __str__(self):
        return f"{self.vendor_id} - {self.name}"


class VendorContact(models.Model):
    """
    Contact persons associated with vendors.
    Supports multiple contacts per vendor with different roles.
    """
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name='contacts'
    )
    
    # Contact Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    title = models.CharField(max_length=100, blank=True)
    email = models.EmailField(validators=[EmailValidator()])
    phone = models.CharField(max_length=20, blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    
    # Role and Responsibilities
    CONTACT_TYPE_CHOICES = [
        ('primary', 'Primary Contact'),
        ('billing', 'Billing Contact'),
        ('technical', 'Technical Contact'),
        ('legal', 'Legal Contact'),
        ('security', 'Security Contact'),
        ('account_manager', 'Account Manager'),
        ('executive', 'Executive Contact'),
        ('emergency', 'Emergency Contact'),
    ]
    contact_type = models.CharField(
        max_length=20,
        choices=CONTACT_TYPE_CHOICES,
        default='primary'
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary contact for this vendor"
    )
    
    # Communication Preferences
    preferred_communication = models.CharField(
        max_length=20,
        choices=[
            ('email', 'Email'),
            ('phone', 'Phone'),
            ('mobile', 'Mobile'),
        ],
        default='email'
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this contact"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_primary', 'contact_type', 'first_name', 'last_name']
        indexes = [
            models.Index(fields=['vendor', 'contact_type']),
            models.Index(fields=['email']),
            models.Index(fields=['is_primary']),
        ]
        unique_together = ['vendor', 'email']  # Prevent duplicate emails per vendor
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __str__(self):
        return f"{self.full_name} ({self.get_contact_type_display()}) - {self.vendor.name}"


class VendorService(models.Model):
    """
    Services provided by vendors with categorization and risk assessment.
    """
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name='services'
    )
    
    # Service Information
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    service_code = models.CharField(
        max_length=50,
        blank=True,
        help_text="Internal service code or SKU"
    )
    
    # Categorization
    SERVICE_CATEGORY_CHOICES = [
        ('it_services', 'IT Services'),
        ('cloud_hosting', 'Cloud Hosting'),
        ('software_licensing', 'Software Licensing'),
        ('consulting', 'Consulting'),
        ('support_maintenance', 'Support & Maintenance'),
        ('professional_services', 'Professional Services'),
        ('managed_services', 'Managed Services'),
        ('security_services', 'Security Services'),
        ('data_processing', 'Data Processing'),
        ('other', 'Other'),
    ]
    category = models.CharField(
        max_length=30,
        choices=SERVICE_CATEGORY_CHOICES,
        default='other'
    )
    
    # Risk and Compliance
    DATA_CLASSIFICATION_CHOICES = [
        ('public', 'Public'),
        ('internal', 'Internal'),
        ('confidential', 'Confidential'),
        ('restricted', 'Restricted'),
    ]
    data_classification = models.CharField(
        max_length=20,
        choices=DATA_CLASSIFICATION_CHOICES,
        default='internal',
        help_text="Highest classification of data processed by this service"
    )
    
    risk_assessment_required = models.BooleanField(
        default=True,
        help_text="Service requires formal risk assessment"
    )
    risk_assessment_completed = models.BooleanField(default=False)
    risk_assessment_date = models.DateField(null=True, blank=True)
    
    # Financial
    cost_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    billing_frequency = models.CharField(
        max_length=20,
        choices=[
            ('one_time', 'One Time'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('annually', 'Annually'),
        ],
        default='monthly'
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['vendor', 'name']
        indexes = [
            models.Index(fields=['vendor', 'category']),
            models.Index(fields=['data_classification']),
            models.Index(fields=['risk_assessment_required']),
            models.Index(fields=['is_active']),
        ]
        unique_together = ['vendor', 'name']  # Prevent duplicate service names per vendor
    
    def __str__(self):
        return f"{self.name} - {self.vendor.name}"


class VendorNote(models.Model):
    """
    Notes and comments about vendors for tracking interactions and decisions.
    """
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name='vendor_notes'
    )
    
    NOTE_TYPE_CHOICES = [
        ('general', 'General'),
        ('meeting', 'Meeting Notes'),
        ('issue', 'Issue/Problem'),
        ('performance', 'Performance Review'),
        ('contract', 'Contract Discussion'),
        ('security', 'Security Assessment'),
        ('compliance', 'Compliance Review'),
        ('renewal', 'Renewal Discussion'),
    ]
    note_type = models.CharField(
        max_length=20,
        choices=NOTE_TYPE_CHOICES,
        default='general'
    )
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    
    # Visibility and Privacy
    is_internal = models.BooleanField(
        default=False,
        help_text="Internal note not visible to vendor"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='vendor_notes'
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vendor', '-created_at']),
            models.Index(fields=['note_type']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.vendor.name}"


class VendorTask(models.Model):
    """
    Vendor-related tasks and activities tracking system.
    Handles contract renewals, security reviews, compliance assessments, and other vendor activities.
    """
    
    # Task Classification
    TASK_TYPE_CHOICES = [
        ('contract_renewal', 'Contract Renewal'),
        ('contract_renegotiation', 'Contract Renegotiation'),
        ('security_review', 'Security Assessment/Review'),
        ('compliance_assessment', 'Compliance Assessment'),
        ('performance_review', 'Performance Review'),
        ('risk_assessment', 'Risk Assessment'),
        ('audit', 'Vendor Audit'),
        ('certification_renewal', 'Certification Renewal'),
        ('policy_review', 'Policy Review'),
        ('onboarding', 'Vendor Onboarding'),
        ('offboarding', 'Vendor Offboarding'),
        ('data_processing_agreement', 'Data Processing Agreement Review'),
        ('insurance_verification', 'Insurance Verification'),
        ('financial_review', 'Financial Review'),
        ('custom', 'Custom Task'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low Priority'),
        ('medium', 'Medium Priority'),
        ('high', 'High Priority'),
        ('urgent', 'Urgent'),
        ('critical', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold'),
    ]
    
    # Core Task Information
    task_id = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique task identifier (auto-generated: TSK-YYYY-NNNN)"
    )
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name='tasks',
        help_text="Associated vendor for this task"
    )
    task_type = models.CharField(
        max_length=30,
        choices=TASK_TYPE_CHOICES,
        help_text="Type of vendor-related task"
    )
    title = models.CharField(
        max_length=200,
        help_text="Descriptive title for the task"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the task requirements"
    )
    
    # Task Scheduling
    due_date = models.DateField(
        help_text="Date when the task is due for completion"
    )
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Optional start date for the task"
    )
    completed_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Actual completion timestamp"
    )
    
    # Task Priority and Status
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Task Assignment and Management
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_vendor_tasks',
        help_text="User responsible for completing this task"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_vendor_tasks',
        help_text="User who created this task"
    )
    
    # Reminder Configuration
    reminder_days = models.JSONField(
        default=lambda: [30, 14, 7, 1],
        help_text="Days before due date to send reminders (e.g., [30, 14, 7, 1])"
    )
    last_reminder_sent = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last reminder sent"
    )
    reminder_recipients = models.JSONField(
        default=list,
        blank=True,
        help_text="Additional email addresses for reminders"
    )
    
    # Task Context and Integration
    related_contract_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Related contract number if applicable"
    )
    service_reference = models.ForeignKey(
        'VendorService',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Related vendor service if applicable"
    )
    
    # Task Results and Documentation
    completion_notes = models.TextField(
        blank=True,
        help_text="Notes about task completion, results, or outcomes"
    )
    attachments = models.JSONField(
        default=list,
        blank=True,
        help_text="References to attached documents or evidence"
    )
    
    # Recurrence Configuration
    is_recurring = models.BooleanField(
        default=False,
        help_text="Whether this task repeats on a schedule"
    )
    recurrence_pattern = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON configuration for recurring tasks (frequency, interval, etc.)"
    )
    parent_task = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recurring_instances',
        help_text="Parent task if this is a recurring instance"
    )
    
    # Automated Task Generation
    auto_generated = models.BooleanField(
        default=False,
        help_text="Whether this task was automatically generated from contract dates"
    )
    generation_source = models.CharField(
        max_length=50,
        blank=True,
        help_text="Source of automatic generation (e.g., 'contract_expiry', 'security_review')"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['due_date', 'priority']
        indexes = [
            models.Index(fields=['task_id']),
            models.Index(fields=['vendor', 'due_date']),
            models.Index(fields=['due_date', 'status']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['task_type']),
            models.Index(fields=['priority', 'due_date']),
            models.Index(fields=['status']),
            models.Index(fields=['auto_generated']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Vendor Task'
        verbose_name_plural = 'Vendor Tasks'
    
    def save(self, *args, **kwargs):
        if not self.task_id:
            self.task_id = self._generate_task_id()
        
        # Auto-update status based on dates
        if self.due_date and not self.completed_date:
            if timezone.now().date() > self.due_date and self.status == 'pending':
                self.status = 'overdue'
        
        # Set completion date when status changes to completed
        if self.status == 'completed' and not self.completed_date:
            self.completed_date = timezone.now()
        elif self.status != 'completed':
            self.completed_date = None
            
        super().save(*args, **kwargs)
        
        # Create recurring instance if needed
        if (self.status == 'completed' and self.is_recurring and 
            not self.parent_task and self.recurrence_pattern):
            self._create_next_recurring_instance()
    
    def _generate_task_id(self):
        """Generate unique task ID in format TSK-YYYY-NNNN"""
        year = timezone.now().year
        last_task = VendorTask.objects.filter(
            task_id__startswith=f'TSK-{year}-'
        ).order_by('task_id').last()
        
        if last_task:
            last_number = int(last_task.task_id.split('-')[-1])
            next_number = last_number + 1
        else:
            next_number = 1
            
        return f'TSK-{year}-{next_number:04d}'
    
    def _create_next_recurring_instance(self):
        """Create next instance of a recurring task"""
        from dateutil.relativedelta import relativedelta
        
        pattern = self.recurrence_pattern
        if not pattern or not pattern.get('frequency'):
            return
            
        frequency = pattern['frequency']  # 'monthly', 'quarterly', 'yearly'
        interval = pattern.get('interval', 1)  # Every N periods
        
        # Calculate next due date
        next_due_date = self.due_date
        if frequency == 'monthly':
            next_due_date = self.due_date + relativedelta(months=interval)
        elif frequency == 'quarterly':
            next_due_date = self.due_date + relativedelta(months=3 * interval)
        elif frequency == 'yearly':
            next_due_date = self.due_date + relativedelta(years=interval)
        
        # Create next instance
        VendorTask.objects.create(
            vendor=self.vendor,
            task_type=self.task_type,
            title=f"{self.title} (Next Instance)",
            description=self.description,
            due_date=next_due_date,
            priority=self.priority,
            assigned_to=self.assigned_to,
            reminder_days=self.reminder_days,
            reminder_recipients=self.reminder_recipients,
            related_contract_number=self.related_contract_number,
            service_reference=self.service_reference,
            is_recurring=True,
            recurrence_pattern=self.recurrence_pattern,
            parent_task=self,
            auto_generated=True,
            generation_source=f'recurring_{self.task_type}',
            created_by=self.created_by
        )
    
    @property
    def is_overdue(self):
        """Check if task is overdue"""
        if self.status == 'completed':
            return False
        return timezone.now().date() > self.due_date
    
    @property
    def days_until_due(self):
        """Calculate days until due date"""
        if self.status == 'completed':
            return None
        delta = self.due_date - timezone.now().date()
        return delta.days
    
    @property
    def should_send_reminder(self):
        """Check if a reminder should be sent today"""
        if self.status == 'completed':
            return False
            
        days_until = self.days_until_due
        if days_until is None or days_until < 0:
            return False
            
        # Check if today matches any reminder day
        return days_until in self.reminder_days
    
    @property
    def next_reminder_date(self):
        """Get the next reminder date"""
        if self.status == 'completed':
            return None
            
        days_until = self.days_until_due
        if days_until is None or days_until < 0:
            return None
        
        # Find the next reminder day
        future_reminders = [day for day in self.reminder_days if day <= days_until]
        if not future_reminders:
            return None
            
        next_reminder_days = min(future_reminders)
        return self.due_date - timezone.timedelta(days=next_reminder_days)
    
    def __str__(self):
        return f"{self.task_id}: {self.title} - {self.vendor.name} (Due: {self.due_date})"