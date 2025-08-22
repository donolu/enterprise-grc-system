from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import RegexValidator
import uuid

User = get_user_model()


class Framework(models.Model):
    """
    Compliance frameworks (SOC2, ISO27001, NIST, PCI-DSS, etc.)
    These are tenant-specific to allow customization.
    """
    FRAMEWORK_TYPES = [
        ('security', 'Security Framework'),
        ('privacy', 'Privacy Framework'), 
        ('financial', 'Financial Framework'),
        ('operational', 'Operational Framework'),
        ('industry', 'Industry-Specific Framework'),
        ('custom', 'Custom Framework'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('deprecated', 'Deprecated'),
        ('archived', 'Archived'),
    ]
    
    # Basic framework information
    name = models.CharField(max_length=200, help_text="Framework name (e.g., SOC 2 Type II)")
    short_name = models.CharField(max_length=50, help_text="Short identifier (e.g., SOC2)")
    description = models.TextField(help_text="Framework description and purpose")
    framework_type = models.CharField(max_length=20, choices=FRAMEWORK_TYPES, default='security')
    
    # Framework identification
    external_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="External framework identifier or reference code"
    )
    issuing_organization = models.CharField(
        max_length=200,
        help_text="Organization that issued/maintains this framework"
    )
    official_url = models.URLField(blank=True, null=True, help_text="Official framework documentation URL")
    
    # Version management
    version = models.CharField(max_length=50, default="1.0", help_text="Framework version")
    effective_date = models.DateField(help_text="Date when this version became effective")
    expiry_date = models.DateField(null=True, blank=True, help_text="Date when this version expires")
    
    # Status and lifecycle
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_mandatory = models.BooleanField(
        default=False, 
        help_text="Whether compliance with this framework is mandatory for the organization"
    )
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_frameworks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Import tracking
    imported_from = models.CharField(
        max_length=200, 
        blank=True, 
        help_text="Source of framework import (file, API, manual entry)"
    )
    import_checksum = models.CharField(
        max_length=64, 
        blank=True,
        help_text="Checksum for tracking changes in imported frameworks"
    )
    
    class Meta:
        ordering = ['name', '-version']
        unique_together = [('name', 'version')]
        indexes = [
            models.Index(fields=['status', 'framework_type']),
            models.Index(fields=['short_name']),
            models.Index(fields=['is_mandatory', 'status']),
        ]
    
    def __str__(self):
        return f"{self.name} v{self.version}"
    
    @property
    def is_active(self):
        return self.status == 'active'
    
    @property
    def clause_count(self):
        return self.clauses.count()
    
    @property
    def control_count(self):
        return sum(clause.controls.count() for clause in self.clauses.all())


class Clause(models.Model):
    """
    Individual clauses/requirements within a compliance framework.
    These map to specific requirements that must be addressed.
    """
    CLAUSE_TYPES = [
        ('control', 'Control Requirement'),
        ('policy', 'Policy Requirement'),
        ('procedure', 'Procedure Requirement'),
        ('documentation', 'Documentation Requirement'),
        ('assessment', 'Assessment Requirement'),
        ('monitoring', 'Monitoring Requirement'),
        ('reporting', 'Reporting Requirement'),
    ]
    
    CRITICALITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    # Framework relationship
    framework = models.ForeignKey(Framework, on_delete=models.CASCADE, related_name='clauses')
    
    # Clause identification
    clause_id = models.CharField(
        max_length=50, 
        help_text="Framework-specific clause identifier (e.g., CC6.1, A.8.2.1)"
    )
    title = models.CharField(max_length=300, help_text="Clause title or heading")
    description = models.TextField(help_text="Full clause text and requirements")
    
    # Clause organization
    parent_clause = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='subclauses',
        help_text="Parent clause for hierarchical organization"
    )
    sort_order = models.PositiveIntegerField(default=0, help_text="Display order within framework")
    
    # Clause properties
    clause_type = models.CharField(max_length=20, choices=CLAUSE_TYPES, default='control')
    criticality = models.CharField(max_length=10, choices=CRITICALITY_LEVELS, default='medium')
    is_testable = models.BooleanField(default=True, help_text="Whether this clause can be tested/audited")
    
    # Implementation guidance
    implementation_guidance = models.TextField(
        blank=True, 
        help_text="Guidance on how to implement this clause"
    )
    testing_procedures = models.TextField(
        blank=True,
        help_text="Procedures for testing compliance with this clause"
    )
    
    # References and mappings
    external_references = models.JSONField(
        default=dict, 
        blank=True,
        help_text="References to other standards, regulations, or frameworks"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['framework', 'sort_order', 'clause_id']
        unique_together = [('framework', 'clause_id')]
        indexes = [
            models.Index(fields=['framework', 'sort_order']),
            models.Index(fields=['clause_type', 'criticality']),
            models.Index(fields=['is_testable']),
        ]
    
    def __str__(self):
        return f"{self.framework.short_name} {self.clause_id}: {self.title}"
    
    @property
    def full_clause_id(self):
        """Get the full hierarchical clause ID."""
        if self.parent_clause:
            return f"{self.parent_clause.full_clause_id}.{self.clause_id}"
        return self.clause_id
    
    @property
    def control_count(self):
        return self.controls.count()
    
    def get_all_subclauses(self):
        """Recursively get all subclauses."""
        subclauses = list(self.subclauses.all())
        for subclause in self.subclauses.all():
            subclauses.extend(subclause.get_all_subclauses())
        return subclauses


class Control(models.Model):
    """
    Internal controls that organizations implement to address framework clauses.
    These are the actual activities, policies, and procedures put in place.
    """
    CONTROL_TYPES = [
        ('preventive', 'Preventive Control'),
        ('detective', 'Detective Control'),
        ('corrective', 'Corrective Control'),
        ('compensating', 'Compensating Control'),
        ('administrative', 'Administrative Control'),
        ('technical', 'Technical Control'),
        ('physical', 'Physical Control'),
    ]
    
    AUTOMATION_LEVELS = [
        ('manual', 'Manual Control'),
        ('semi_automated', 'Semi-Automated Control'),
        ('automated', 'Automated Control'),
        ('continuous', 'Continuous Monitoring'),
    ]
    
    EFFECTIVENESS_RATINGS = [
        ('not_effective', 'Not Effective'),
        ('partially_effective', 'Partially Effective'),
        ('largely_effective', 'Largely Effective'),
        ('fully_effective', 'Fully Effective'),
    ]
    
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('implemented', 'Implemented'),
        ('testing', 'Under Testing'),
        ('active', 'Active'),
        ('remediation', 'Needs Remediation'),
        ('disabled', 'Disabled'),
        ('retired', 'Retired'),
    ]
    
    # Basic control information
    name = models.CharField(max_length=200, help_text="Control name or title")
    description = models.TextField(help_text="Detailed control description")
    control_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique control identifier",
        validators=[RegexValidator(
            regex=r'^[A-Z0-9][A-Z0-9\-\.]*$',
            message='Control ID must start with alphanumeric and contain only uppercase letters, numbers, hyphens, and dots'
        )]
    )
    
    # Framework mappings - many-to-many since controls can address multiple clauses
    clauses = models.ManyToManyField(
        Clause, 
        related_name='controls',
        help_text="Framework clauses this control addresses"
    )
    
    # Control properties
    control_type = models.CharField(max_length=20, choices=CONTROL_TYPES)
    automation_level = models.CharField(max_length=20, choices=AUTOMATION_LEVELS, default='manual')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    
    # Control ownership and responsibility
    control_owner = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='owned_controls',
        help_text="Person responsible for this control"
    )
    business_owner = models.CharField(
        max_length=200, 
        blank=True,
        help_text="Business unit or department responsible"
    )
    
    # Implementation details
    implementation_details = models.TextField(
        blank=True,
        help_text="Specific implementation steps and procedures"
    )
    frequency = models.CharField(
        max_length=100,
        blank=True, 
        help_text="How often this control is performed (e.g., daily, monthly, annually)"
    )
    
    # Effectiveness and testing
    last_tested_date = models.DateField(null=True, blank=True)
    last_test_result = models.CharField(
        max_length=20, 
        choices=EFFECTIVENESS_RATINGS,
        blank=True
    )
    effectiveness_rating = models.CharField(
        max_length=20,
        choices=EFFECTIVENESS_RATINGS,
        blank=True,
        help_text="Current effectiveness assessment"
    )
    
    # Evidence and documentation
    evidence_requirements = models.TextField(
        blank=True,
        help_text="What evidence is needed to demonstrate this control's effectiveness"
    )
    documentation_links = models.JSONField(
        default=list,
        blank=True,
        help_text="Links to related policies, procedures, and documentation"
    )
    
    # Risk and remediation
    risk_rating = models.CharField(
        max_length=10,
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')],
        blank=True,
        help_text="Risk level if this control fails"
    )
    remediation_plan = models.TextField(
        blank=True,
        help_text="Plan for addressing control deficiencies"
    )
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_controls')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Version tracking
    version = models.CharField(max_length=20, default="1.0")
    change_log = models.JSONField(
        default=list,
        blank=True,
        help_text="History of changes to this control"
    )
    
    class Meta:
        ordering = ['control_id', 'name']
        indexes = [
            models.Index(fields=['status', 'control_type']),
            models.Index(fields=['control_owner']),
            models.Index(fields=['automation_level']),
            models.Index(fields=['last_tested_date']),
            models.Index(fields=['effectiveness_rating']),
        ]
    
    def __str__(self):
        return f"{self.control_id}: {self.name}"
    
    @property
    def is_active(self):
        return self.status == 'active'
    
    @property
    def needs_testing(self):
        """Check if control needs testing based on frequency and last test date."""
        if not self.last_tested_date:
            return True
        
        # Simple logic - could be enhanced with frequency parsing
        days_since_test = (timezone.now().date() - self.last_tested_date).days
        return days_since_test > 90  # Default 90-day testing cycle
    
    @property
    def framework_coverage(self):
        """Get list of frameworks this control addresses."""
        return list(set(clause.framework for clause in self.clauses.all()))
    
    def add_change_log_entry(self, user, change_description):
        """Add an entry to the control's change log."""
        if not self.change_log:
            self.change_log = []
        
        entry = {
            'timestamp': timezone.now().isoformat(),
            'user': user.username if user else 'System',
            'description': change_description
        }
        self.change_log.append(entry)
        self.save(update_fields=['change_log'])


class ControlEvidence(models.Model):
    """
    Evidence documents and artifacts that demonstrate control effectiveness.
    """
    EVIDENCE_TYPES = [
        ('document', 'Document/Policy'),
        ('screenshot', 'Screenshot'),
        ('log_file', 'Log File'),
        ('report', 'Report'),
        ('certificate', 'Certificate'),
        ('approval', 'Approval/Sign-off'),
        ('test_result', 'Test Result'),
        ('meeting_notes', 'Meeting Notes'),
        ('other', 'Other'),
    ]
    
    control = models.ForeignKey(Control, on_delete=models.CASCADE, related_name='evidence')
    
    # Evidence details
    title = models.CharField(max_length=200, help_text="Evidence title or description")
    evidence_type = models.CharField(max_length=20, choices=EVIDENCE_TYPES)
    description = models.TextField(blank=True, help_text="Additional evidence description")
    
    # File storage - references Document model for file management
    document = models.ForeignKey(
        'core.Document', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="Associated document file"
    )
    external_url = models.URLField(
        blank=True, 
        null=True,
        help_text="External URL for evidence (e.g., system screenshot)"
    )
    
    # Evidence metadata
    evidence_date = models.DateField(
        default=timezone.now,
        help_text="Date when evidence was created or collected"
    )
    collected_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        help_text="Person who collected this evidence"
    )
    
    # Validation
    is_validated = models.BooleanField(default=False, help_text="Whether evidence has been validated")
    validated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='validated_evidence',
        help_text="Person who validated this evidence"
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    validation_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-evidence_date', '-created_at']
        indexes = [
            models.Index(fields=['control', '-evidence_date']),
            models.Index(fields=['evidence_type']),
            models.Index(fields=['is_validated']),
        ]
    
    def __str__(self):
        return f"{self.control.control_id} - {self.title}"
    
    def validate_evidence(self, validator_user, notes=""):
        """Mark evidence as validated."""
        self.is_validated = True
        self.validated_by = validator_user
        self.validated_at = timezone.now()
        self.validation_notes = notes
        self.save()


class FrameworkMapping(models.Model):
    """
    Mappings between different frameworks to show relationships and crosswalks.
    Useful for organizations that need to comply with multiple frameworks.
    """
    MAPPING_TYPES = [
        ('equivalent', 'Equivalent Requirements'),
        ('partial', 'Partially Overlapping'),
        ('supports', 'Supporting Requirement'),
        ('related', 'Related Requirement'),
    ]
    
    # Source and target clauses
    source_clause = models.ForeignKey(
        Clause, 
        on_delete=models.CASCADE, 
        related_name='source_mappings'
    )
    target_clause = models.ForeignKey(
        Clause, 
        on_delete=models.CASCADE, 
        related_name='target_mappings'
    )
    
    # Mapping details
    mapping_type = models.CharField(max_length=20, choices=MAPPING_TYPES)
    mapping_rationale = models.TextField(
        blank=True,
        help_text="Explanation of why these clauses are mapped together"
    )
    confidence_level = models.IntegerField(
        default=75,
        help_text="Confidence percentage (0-100) in this mapping"
    )
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='verified_mappings'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = [('source_clause', 'target_clause')]
        indexes = [
            models.Index(fields=['mapping_type']),
            models.Index(fields=['confidence_level']),
        ]
    
    def __str__(self):
        return f"{self.source_clause.framework.short_name} {self.source_clause.clause_id} ↔ {self.target_clause.framework.short_name} {self.target_clause.clause_id}"