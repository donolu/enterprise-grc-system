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


class ControlAssessment(models.Model):
    """
    Tenant-specific assessments of controls for compliance frameworks.
    Links controls to organizational implementation and compliance status.
    """
    APPLICABILITY_CHOICES = [
        ('applicable', 'Applicable'),
        ('not_applicable', 'Not Applicable'),
        ('to_be_determined', 'To Be Determined'),
    ]
    
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('under_review', 'Under Review'),
        ('complete', 'Complete'),
        ('not_applicable', 'Not Applicable'),
        ('deferred', 'Deferred'),
    ]
    
    IMPLEMENTATION_STATUS_CHOICES = [
        ('not_implemented', 'Not Implemented'),
        ('partially_implemented', 'Partially Implemented'),
        ('implemented', 'Implemented'),
        ('not_applicable', 'Not Applicable'),
    ]
    
    MATURITY_LEVELS = [
        ('ad_hoc', 'Ad Hoc'),
        ('repeatable', 'Repeatable'),
        ('defined', 'Defined'),
        ('managed', 'Managed'),
        ('optimized', 'Optimized'),
    ]
    
    # Core relationships
    control = models.ForeignKey(
        Control, 
        on_delete=models.CASCADE, 
        related_name='assessments',
        help_text="The control being assessed"
    )
    
    # Assessment metadata
    assessment_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique assessment identifier"
    )
    
    # Applicability determination
    applicability = models.CharField(
        max_length=20,
        choices=APPLICABILITY_CHOICES,
        default='to_be_determined',
        help_text="Whether this control applies to the organization"
    )
    applicability_rationale = models.TextField(
        blank=True,
        help_text="Explanation of why the control is/isn't applicable"
    )
    
    # Assessment status and progress
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='not_started',
        help_text="Current assessment status"
    )
    implementation_status = models.CharField(
        max_length=25,
        choices=IMPLEMENTATION_STATUS_CHOICES,
        default='not_implemented',
        help_text="Current implementation status of the control"
    )
    
    # Ownership and responsibility
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_assessments',
        help_text="Person responsible for completing this assessment"
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='review_assessments',
        help_text="Person responsible for reviewing this assessment"
    )
    
    # Timeline management
    due_date = models.DateField(
        null=True,
        blank=True,
        help_text="Target completion date for this assessment"
    )
    started_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when assessment work began"
    )
    completed_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when assessment was completed"
    )
    
    # Assessment details
    current_state_description = models.TextField(
        blank=True,
        help_text="Description of the current state of control implementation"
    )
    target_state_description = models.TextField(
        blank=True,
        help_text="Description of the desired future state"
    )
    gap_analysis = models.TextField(
        blank=True,
        help_text="Analysis of gaps between current and target state"
    )
    
    # Implementation details
    implementation_approach = models.TextField(
        blank=True,
        help_text="Planned or implemented approach for addressing this control"
    )
    maturity_level = models.CharField(
        max_length=20,
        choices=MATURITY_LEVELS,
        blank=True,
        help_text="Current maturity level of control implementation"
    )
    
    # Risk and compliance
    risk_rating = models.CharField(
        max_length=10,
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')],
        blank=True,
        help_text="Risk level if this control is not properly implemented"
    )
    compliance_score = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Compliance score (0-100) for this control"
    )
    
    # Notes and comments
    assessment_notes = models.TextField(
        blank=True,
        help_text="General notes and observations about this assessment"
    )
    reviewer_comments = models.TextField(
        blank=True,
        help_text="Comments from the reviewer"
    )
    
    # Remediation planning
    remediation_plan = models.TextField(
        blank=True,
        help_text="Plan for addressing gaps and improving control implementation"
    )
    remediation_due_date = models.DateField(
        null=True,
        blank=True,
        help_text="Target date for completing remediation activities"
    )
    remediation_owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='remediation_assignments',
        help_text="Person responsible for remediation activities"
    )
    
    # Audit and tracking
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_assessments',
        help_text="Person who created this assessment"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Assessment history and versioning
    version = models.PositiveIntegerField(default=1, help_text="Assessment version number")
    change_log = models.JSONField(
        default=list,
        blank=True,
        help_text="History of changes to this assessment"
    )
    
    class Meta:
        ordering = ['control__control_id', 'due_date']
        indexes = [
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['applicability', 'implementation_status']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['control', 'status']),
        ]
        unique_together = [('control', 'assessment_id')]
    
    def __str__(self):
        return f"Assessment {self.assessment_id}: {self.control.control_id}"
    
    @property
    def is_overdue(self):
        """Check if assessment is overdue."""
        if not self.due_date:
            return False
        return self.due_date < timezone.now().date() and self.status not in ['complete', 'not_applicable']
    
    @property
    def is_complete(self):
        """Check if assessment is complete."""
        return self.status == 'complete'
    
    @property
    def completion_percentage(self):
        """Calculate completion percentage based on status."""
        status_weights = {
            'not_started': 0,
            'pending': 10,
            'in_progress': 50,
            'under_review': 80,
            'complete': 100,
            'not_applicable': 100,
            'deferred': 0,
        }
        return status_weights.get(self.status, 0)
    
    @property
    def days_until_due(self):
        """Calculate days until due date."""
        if not self.due_date:
            return None
        delta = self.due_date - timezone.now().date()
        return delta.days
    
    def save(self, *args, **kwargs):
        # Auto-generate assessment_id if not provided
        if not self.assessment_id:
            self.assessment_id = f"ASS-{self.control.control_id}-{uuid.uuid4().hex[:8].upper()}"
        
        # Update status-based dates
        if self.status == 'in_progress' and not self.started_date:
            self.started_date = timezone.now().date()
        elif self.status == 'complete' and not self.completed_date:
            self.completed_date = timezone.now().date()
        
        super().save(*args, **kwargs)
    
    def add_change_log_entry(self, user, change_description):
        """Add an entry to the assessment's change log."""
        if not self.change_log:
            self.change_log = []
        
        entry = {
            'timestamp': timezone.now().isoformat(),
            'user': user.username if user else 'System',
            'description': change_description,
            'version': self.version
        }
        self.change_log.append(entry)
        self.save(update_fields=['change_log'])
    
    def update_status(self, new_status, user=None, notes=""):
        """Update assessment status with logging."""
        old_status = self.status
        self.status = new_status
        
        # Log the change
        change_description = f'Status updated from "{old_status}" to "{new_status}"'
        if notes:
            change_description += f'. Notes: {notes}'
        
        if user:
            self.add_change_log_entry(user, change_description)
        
        self.save()


class AssessmentEvidence(models.Model):
    """
    Evidence specifically collected for control assessments.
    Links assessment evidence to the ControlEvidence model.
    """
    assessment = models.ForeignKey(
        ControlAssessment, 
        on_delete=models.CASCADE, 
        related_name='evidence_links'
    )
    evidence = models.ForeignKey(
        ControlEvidence, 
        on_delete=models.CASCADE, 
        related_name='assessment_links'
    )
    
    # Evidence relationship to assessment
    evidence_purpose = models.CharField(
        max_length=100,
        blank=True,
        help_text="Purpose of this evidence for the assessment"
    )
    is_primary_evidence = models.BooleanField(
        default=False,
        help_text="Whether this is primary evidence for the assessment"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        unique_together = [('assessment', 'evidence')]
        indexes = [
            models.Index(fields=['assessment', 'is_primary_evidence']),
        ]
    
    def __str__(self):
        return f"{self.assessment.assessment_id} - {self.evidence.title}"


class AssessmentReminderConfiguration(models.Model):
    """
    Configuration for automated assessment reminders per user.
    """
    REMINDER_FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('custom', 'Custom Days'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='reminder_config',
        help_text="User for whom reminders are configured"
    )
    
    # Reminder timing settings
    enable_reminders = models.BooleanField(
        default=True,
        help_text="Whether to send automated reminders to this user"
    )
    advance_warning_days = models.PositiveIntegerField(
        default=7,
        help_text="Days before due date to send first reminder"
    )
    overdue_reminders = models.BooleanField(
        default=True,
        help_text="Whether to send reminders for overdue assessments"
    )
    reminder_frequency = models.CharField(
        max_length=10,
        choices=REMINDER_FREQUENCY_CHOICES,
        default='daily',
        help_text="How frequently to send overdue reminders"
    )
    custom_reminder_days = models.JSONField(
        default=list,
        blank=True,
        help_text="Custom days for reminders (e.g., [1, 3, 7] for 1, 3, and 7 days before)"
    )
    
    # Email preferences
    email_notifications = models.BooleanField(
        default=True,
        help_text="Whether to send email notifications"
    )
    include_assessment_details = models.BooleanField(
        default=True,
        help_text="Whether to include detailed assessment information in emails"
    )
    include_remediation_items = models.BooleanField(
        default=True,
        help_text="Whether to include remediation due dates in reminders"
    )
    
    # Digest settings
    daily_digest_enabled = models.BooleanField(
        default=False,
        help_text="Whether to send daily digest of all upcoming/overdue items"
    )
    weekly_digest_enabled = models.BooleanField(
        default=True,
        help_text="Whether to send weekly digest of upcoming assessments"
    )
    digest_day_of_week = models.PositiveIntegerField(
        default=1,  # Monday
        help_text="Day of week for weekly digest (0=Sunday, 1=Monday, etc.)"
    )
    
    # Auto-silence settings
    silence_completed_assessments = models.BooleanField(
        default=True,
        help_text="Stop sending reminders for completed assessments"
    )
    silence_not_applicable = models.BooleanField(
        default=True,
        help_text="Don't send reminders for assessments marked as not applicable"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Assessment Reminder Configuration"
        verbose_name_plural = "Assessment Reminder Configurations"
    
    def __str__(self):
        return f"Reminder config for {self.user.username}"
    
    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create reminder configuration for a user with defaults."""
        config, created = cls.objects.get_or_create(
            user=user,
            defaults={
                'enable_reminders': True,
                'advance_warning_days': 7,
                'overdue_reminders': True,
                'email_notifications': True,
                'weekly_digest_enabled': True,
            }
        )
        return config
    
    def get_reminder_days(self):
        """Get list of days before due date when reminders should be sent."""
        if self.reminder_frequency == 'custom' and self.custom_reminder_days:
            return sorted(self.custom_reminder_days, reverse=True)
        elif self.reminder_frequency == 'weekly':
            return [7, 14, 21]  # Weekly reminders
        else:  # daily
            return list(range(1, self.advance_warning_days + 1))


class AssessmentReminderLog(models.Model):
    """
    Log of sent reminders to prevent duplicate notifications.
    """
    REMINDER_TYPES = [
        ('advance_warning', 'Advance Warning'),
        ('due_today', 'Due Today'),
        ('overdue', 'Overdue'),
        ('weekly_digest', 'Weekly Digest'),
        ('daily_digest', 'Daily Digest'),
    ]
    
    assessment = models.ForeignKey(
        ControlAssessment,
        on_delete=models.CASCADE,
        related_name='reminder_logs'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assessment_reminder_logs'
    )
    reminder_type = models.CharField(
        max_length=20,
        choices=REMINDER_TYPES
    )
    days_before_due = models.IntegerField(
        null=True,
        blank=True,
        help_text="Days before due date when reminder was sent (negative for overdue)"
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    email_sent = models.BooleanField(default=False)
    
    class Meta:
        unique_together = [('assessment', 'user', 'reminder_type', 'days_before_due')]
        indexes = [
            models.Index(fields=['assessment', 'user']),
            models.Index(fields=['sent_at']),
            models.Index(fields=['reminder_type']),
        ]
    
    def __str__(self):
        return f"{self.reminder_type} reminder for {self.assessment.assessment_id} to {self.user.username}"