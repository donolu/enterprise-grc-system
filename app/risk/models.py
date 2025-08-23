from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid

User = get_user_model()


class RiskCategory(models.Model):
    """
    Risk categories for organizing and classifying risks.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#6B7280', help_text='Hex color code for UI display')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Risk Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class RiskMatrix(models.Model):
    """
    Configurable risk matrix for calculating risk ratings.
    Supports multiple matrix configurations for different risk types.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    
    # Matrix dimensions (typically 5x5 or 4x4)
    impact_levels = models.PositiveIntegerField(default=5, validators=[MinValueValidator(3), MaxValueValidator(7)])
    likelihood_levels = models.PositiveIntegerField(default=5, validators=[MinValueValidator(3), MaxValueValidator(7)])
    
    # JSON field to store the matrix configuration
    # Format: {"1": {"1": "low", "2": "low", ...}, "2": {...}, ...}
    matrix_config = models.JSONField(default=dict, help_text='Matrix configuration mapping impact x likelihood to risk levels')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_risk_matrices')

    class Meta:
        verbose_name_plural = "Risk Matrices"
        ordering = ['-is_default', 'name']

    def __str__(self):
        return f"{self.name} ({self.impact_levels}x{self.likelihood_levels})"

    def save(self, *args, **kwargs):
        # Ensure only one default matrix
        if self.is_default:
            RiskMatrix.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        
        # Create default matrix configuration if not provided
        if not self.matrix_config:
            self.matrix_config = self._generate_default_matrix()
        
        super().save(*args, **kwargs)

    def _generate_default_matrix(self):
        """Generate a default 5x5 risk matrix configuration."""
        config = {}
        for impact in range(1, self.impact_levels + 1):
            config[str(impact)] = {}
            for likelihood in range(1, self.likelihood_levels + 1):
                # Simple calculation: sum of impact + likelihood
                total = impact + likelihood
                if total <= 3:
                    level = 'low'
                elif total <= 5:
                    level = 'medium'
                elif total <= 7:
                    level = 'high'
                else:
                    level = 'critical'
                config[str(impact)][str(likelihood)] = level
        return config

    def calculate_risk_level(self, impact, likelihood):
        """Calculate risk level based on impact and likelihood."""
        if not self.matrix_config:
            return 'medium'  # Default fallback
        
        impact_str = str(min(max(1, impact), self.impact_levels))
        likelihood_str = str(min(max(1, likelihood), self.likelihood_levels))
        
        return self.matrix_config.get(impact_str, {}).get(likelihood_str, 'medium')


class Risk(models.Model):
    """
    Main Risk model representing identified risks and their assessments.
    """
    RISK_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('identified', 'Identified'),
        ('assessed', 'Assessed'),
        ('treatment_planned', 'Treatment Planned'),
        ('treatment_in_progress', 'Treatment in Progress'),
        ('mitigated', 'Mitigated'),
        ('accepted', 'Accepted'),
        ('transferred', 'Transferred'),
        ('closed', 'Closed'),
    ]
    
    TREATMENT_STRATEGIES = [
        ('mitigate', 'Mitigate'),
        ('accept', 'Accept'),
        ('transfer', 'Transfer'),
        ('avoid', 'Avoid'),
    ]

    # Basic identification
    risk_id = models.CharField(max_length=50, unique=True, help_text='Unique risk identifier')
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(RiskCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='risks')
    
    # Risk assessment
    impact = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Impact level (1=Very Low, 5=Very High)'
    )
    likelihood = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Likelihood level (1=Very Low, 5=Very High)'
    )
    risk_level = models.CharField(max_length=20, choices=RISK_LEVELS, help_text='Calculated risk level')
    risk_matrix = models.ForeignKey(RiskMatrix, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Risk management
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='identified')
    treatment_strategy = models.CharField(max_length=20, choices=TREATMENT_STRATEGIES, blank=True)
    treatment_description = models.TextField(blank=True, help_text='Description of the treatment approach')
    
    # Ownership and responsibility
    risk_owner = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='owned_risks',
        help_text='Person responsible for managing this risk'
    )
    
    # Dates
    identified_date = models.DateField(default=timezone.now)
    last_assessed_date = models.DateField(null=True, blank=True)
    next_review_date = models.DateField(null=True, blank=True)
    closed_date = models.DateField(null=True, blank=True)
    
    # Additional context
    potential_impact_description = models.TextField(blank=True, help_text='Detailed description of potential impact')
    current_controls = models.TextField(blank=True, help_text='Existing controls or mitigations in place')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_risks')

    class Meta:
        ordering = ['-risk_level', '-impact', '-likelihood', 'title']
        indexes = [
            models.Index(fields=['status', 'risk_level']),
            models.Index(fields=['risk_owner', 'status']),
            models.Index(fields=['next_review_date']),
            models.Index(fields=['category', 'risk_level']),
        ]

    def __str__(self):
        return f"{self.risk_id}: {self.title}"

    def save(self, *args, **kwargs):
        # Auto-generate risk_id if not provided
        if not self.risk_id:
            self.risk_id = self._generate_risk_id()
        
        # Calculate risk level based on impact and likelihood
        self.risk_level = self._calculate_risk_level()
        
        # Update last assessed date when impact or likelihood changes
        if self.pk:
            original = Risk.objects.get(pk=self.pk)
            if original.impact != self.impact or original.likelihood != self.likelihood:
                self.last_assessed_date = timezone.now().date()
        else:
            self.last_assessed_date = timezone.now().date()
        
        # Auto-set closed date when status changes to closed
        if self.status == 'closed' and not self.closed_date:
            self.closed_date = timezone.now().date()
        elif self.status != 'closed' and self.closed_date:
            self.closed_date = None
        
        super().save(*args, **kwargs)

    def _generate_risk_id(self):
        """Generate a unique risk ID."""
        # Get current year and a sequence number
        year = timezone.now().year
        existing_count = Risk.objects.filter(
            risk_id__startswith=f'RISK-{year}'
        ).count()
        return f'RISK-{year}-{existing_count + 1:04d}'

    def _calculate_risk_level(self):
        """Calculate risk level based on impact, likelihood, and risk matrix."""
        if self.risk_matrix:
            return self.risk_matrix.calculate_risk_level(self.impact, self.likelihood)
        
        # Default calculation if no matrix is specified
        default_matrix = RiskMatrix.objects.filter(is_default=True).first()
        if default_matrix:
            return default_matrix.calculate_risk_level(self.impact, self.likelihood)
        
        # Fallback calculation
        total = self.impact + self.likelihood
        if total <= 3:
            return 'low'
        elif total <= 5:
            return 'medium'
        elif total <= 7:
            return 'high'
        else:
            return 'critical'

    @property
    def risk_score(self):
        """Numerical risk score (impact * likelihood)."""
        return self.impact * self.likelihood

    @property
    def is_overdue_for_review(self):
        """Check if risk is overdue for review."""
        if not self.next_review_date:
            return False
        return self.next_review_date < timezone.now().date()

    @property
    def days_until_review(self):
        """Days until next review (negative if overdue)."""
        if not self.next_review_date:
            return None
        delta = self.next_review_date - timezone.now().date()
        return delta.days

    @property
    def is_active(self):
        """Check if risk is in an active state."""
        return self.status not in ['closed', 'transferred']

    def get_risk_level_color(self):
        """Get color code for risk level."""
        colors = {
            'low': '#10B981',      # Green
            'medium': '#F59E0B',   # Yellow
            'high': '#EF4444',     # Red
            'critical': '#DC2626', # Dark Red
        }
        return colors.get(self.risk_level, '#6B7280')

    def get_status_display_color(self):
        """Get color code for status."""
        colors = {
            'identified': '#6B7280',         # Gray
            'assessed': '#3B82F6',           # Blue
            'treatment_planned': '#8B5CF6',  # Purple
            'treatment_in_progress': '#F59E0B', # Yellow
            'mitigated': '#10B981',          # Green
            'accepted': '#6B7280',           # Gray
            'transferred': '#6B7280',        # Gray
            'closed': '#374151',             # Dark Gray
        }
        return colors.get(self.status, '#6B7280')


class RiskNote(models.Model):
    """
    Notes and comments associated with risks for tracking progress and decisions.
    """
    risk = models.ForeignKey(Risk, on_delete=models.CASCADE, related_name='notes')
    note = models.TextField()
    note_type = models.CharField(
        max_length=30,
        choices=[
            ('general', 'General'),
            ('assessment', 'Assessment'),
            ('treatment', 'Treatment'),
            ('review', 'Review'),
            ('status_change', 'Status Change'),
        ],
        default='general'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='risk_notes')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Note for {self.risk.risk_id} by {self.created_by}"


class RiskAction(models.Model):
    """
    Risk treatment actions for implementing risk mitigation, acceptance, transfer, or avoidance strategies.
    These actions represent specific tasks or activities required to address identified risks.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('deferred', 'Deferred'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    ACTION_TYPES = [
        ('preventive', 'Preventive Control'),
        ('detective', 'Detective Control'),
        ('corrective', 'Corrective Action'),
        ('policy', 'Policy/Procedure'),
        ('training', 'Training/Awareness'),
        ('technical', 'Technical Implementation'),
        ('assessment', 'Assessment/Review'),
        ('other', 'Other'),
    ]

    # Basic identification
    action_id = models.CharField(max_length=50, unique=True, help_text='Unique action identifier')
    risk = models.ForeignKey(Risk, on_delete=models.CASCADE, related_name='actions')
    title = models.CharField(max_length=200)
    description = models.TextField()
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES, default='other')
    
    # Assignment and ownership
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_risk_actions',
        help_text='Person responsible for completing this action'
    )
    
    # Status and priority
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    
    # Dates and scheduling
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(help_text='Date when this action must be completed')
    completed_date = models.DateField(null=True, blank=True)
    
    # Progress tracking
    progress_percentage = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Completion percentage (0-100)'
    )
    
    # Cost and effort estimation
    estimated_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Estimated cost to complete this action'
    )
    actual_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Actual cost incurred for this action'
    )
    estimated_effort_hours = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Estimated effort in hours'
    )
    
    # Additional context
    success_criteria = models.TextField(
        blank=True,
        help_text='Specific criteria that define successful completion'
    )
    dependencies = models.TextField(
        blank=True,
        help_text='Dependencies or prerequisites for this action'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_risk_actions')

    class Meta:
        ordering = ['due_date', '-priority', 'title']
        indexes = [
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['risk', 'status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['priority', 'status']),
        ]

    def __str__(self):
        return f"{self.action_id}: {self.title}"

    def save(self, *args, **kwargs):
        # Auto-generate action_id if not provided
        if not self.action_id:
            self.action_id = self._generate_action_id()
        
        # Auto-set completed date when status changes to completed
        if self.status == 'completed' and not self.completed_date:
            self.completed_date = timezone.now().date()
            self.progress_percentage = 100
        elif self.status != 'completed' and self.completed_date:
            self.completed_date = None
        
        super().save(*args, **kwargs)

    def _generate_action_id(self):
        """Generate a unique risk action ID."""
        # Get current year and a sequence number
        year = timezone.now().year
        existing_count = RiskAction.objects.filter(
            action_id__startswith=f'RA-{year}'
        ).count()
        return f'RA-{year}-{existing_count + 1:04d}'

    @property
    def is_overdue(self):
        """Check if action is overdue."""
        if self.status in ['completed', 'cancelled']:
            return False
        return self.due_date < timezone.now().date()

    @property
    def days_until_due(self):
        """Days until due date (negative if overdue)."""
        delta = self.due_date - timezone.now().date()
        return delta.days

    @property
    def is_due_soon(self, days_threshold=7):
        """Check if action is due within the threshold."""
        return 0 <= self.days_until_due <= days_threshold

    def get_priority_color(self):
        """Get color code for priority level."""
        colors = {
            'low': '#10B981',      # Green
            'medium': '#F59E0B',   # Yellow
            'high': '#EF4444',     # Red
            'critical': '#DC2626', # Dark Red
        }
        return colors.get(self.priority, '#6B7280')

    def get_status_color(self):
        """Get color code for status."""
        colors = {
            'pending': '#6B7280',           # Gray
            'in_progress': '#3B82F6',       # Blue
            'completed': '#10B981',         # Green
            'cancelled': '#EF4444',         # Red
            'deferred': '#F59E0B',          # Yellow
        }
        return colors.get(self.status, '#6B7280')


class RiskActionNote(models.Model):
    """
    Progress notes and updates for risk actions.
    """
    action = models.ForeignKey(RiskAction, on_delete=models.CASCADE, related_name='notes')
    note = models.TextField()
    note_type = models.CharField(
        max_length=30,
        choices=[
            ('progress', 'Progress Update'),
            ('issue', 'Issue/Blocker'),
            ('completion', 'Completion'),
            ('status_change', 'Status Change'),
            ('general', 'General'),
        ],
        default='progress'
    )
    
    progress_percentage = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Progress percentage at time of note'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='risk_action_notes')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Note for {self.action.action_id} by {self.created_by}"


class RiskActionEvidence(models.Model):
    """
    Evidence files and documentation supporting completion of risk actions.
    """
    EVIDENCE_TYPES = [
        ('document', 'Document/Policy'),
        ('screenshot', 'Screenshot'),
        ('report', 'Report/Analysis'),
        ('certificate', 'Certificate'),
        ('configuration', 'Configuration File'),
        ('training_record', 'Training Record'),
        ('audit_log', 'Audit Log'),
        ('other', 'Other'),
    ]

    action = models.ForeignKey(RiskAction, on_delete=models.CASCADE, related_name='evidence')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    evidence_type = models.CharField(max_length=20, choices=EVIDENCE_TYPES, default='document')
    
    # File storage - using same pattern as existing evidence system
    file = models.FileField(upload_to='risk_action_evidence/', null=True, blank=True)
    external_link = models.URLField(blank=True, help_text='Link to external evidence or system')
    
    # Validation
    is_validated = models.BooleanField(default=False)
    validated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='validated_risk_action_evidence'
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    validation_notes = models.TextField(blank=True)
    
    # Metadata
    evidence_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_risk_action_evidence')

    class Meta:
        ordering = ['-evidence_date', '-created_at']
        indexes = [
            models.Index(fields=['action', '-evidence_date']),
            models.Index(fields=['evidence_type']),
            models.Index(fields=['is_validated']),
        ]

    def __str__(self):
        return f"{self.action.action_id} - {self.title}"

    def validate_evidence(self, validator_user, notes=""):
        """Mark evidence as validated."""
        self.is_validated = True
        self.validated_by = validator_user
        self.validated_at = timezone.now()
        self.validation_notes = notes
        self.save()


class RiskActionReminderConfiguration(models.Model):
    """
    Configuration for automated risk action reminders per user.
    Extends the existing reminder system pattern for risk actions.
    """
    REMINDER_FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('custom', 'Custom Days'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='risk_action_reminder_config',
        help_text="User for whom risk action reminders are configured"
    )
    
    # Reminder timing settings
    enable_reminders = models.BooleanField(
        default=True,
        help_text="Whether to send automated reminders to this user"
    )
    advance_warning_days = models.PositiveIntegerField(
        default=7,
        help_text="Days before due date to send advance warning"
    )
    reminder_frequency = models.CharField(
        max_length=10,
        choices=REMINDER_FREQUENCY_CHOICES,
        default='daily',
        help_text="How frequently to send reminders"
    )
    custom_reminder_days = models.JSONField(
        default=list,
        blank=True,
        help_text="Custom reminder days pattern [1, 3, 7, 14] - only used when frequency is 'custom'"
    )
    
    # Email notification settings
    email_notifications = models.BooleanField(
        default=True,
        help_text="Send email notifications"
    )
    overdue_reminders = models.BooleanField(
        default=True,
        help_text="Send reminders for overdue actions"
    )
    weekly_digest_enabled = models.BooleanField(
        default=True,
        help_text="Send weekly summary digest"
    )
    weekly_digest_day = models.PositiveIntegerField(
        default=1,  # Monday
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        help_text="Day of week for digest (0=Monday, 6=Sunday)"
    )
    
    # Auto-silence settings
    silence_completed = models.BooleanField(
        default=True,
        help_text="Stop sending reminders for completed actions"
    )
    silence_cancelled = models.BooleanField(
        default=True,
        help_text="Stop sending reminders for cancelled actions"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Risk Action Reminder Configuration"
        verbose_name_plural = "Risk Action Reminder Configurations"

    def __str__(self):
        return f"Risk Action Reminders for {self.user.username}"

    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create reminder configuration for user with defaults."""
        config, created = cls.objects.get_or_create(
            user=user,
            defaults={
                'enable_reminders': True,
                'advance_warning_days': 7,
                'email_notifications': True,
                'weekly_digest_enabled': True,
            }
        )
        return config

    def get_reminder_days(self):
        """Get list of days when reminders should be sent before due date."""
        if self.reminder_frequency == 'custom' and self.custom_reminder_days:
            return sorted(self.custom_reminder_days, reverse=True)
        elif self.reminder_frequency == 'weekly':
            return [7]  # Weekly reminders 7 days before
        else:  # daily
            return list(range(1, self.advance_warning_days + 1))


class RiskActionReminderLog(models.Model):
    """
    Log of sent risk action reminders to prevent duplicates and track delivery.
    """
    REMINDER_TYPES = [
        ('advance_warning', 'Advance Warning'),
        ('due_today', 'Due Today'),
        ('overdue', 'Overdue'),
        ('weekly_digest', 'Weekly Digest'),
        ('assignment', 'Assignment Notification'),
    ]
    
    action = models.ForeignKey(RiskAction, on_delete=models.CASCADE, related_name='reminder_logs')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='risk_action_reminder_logs')
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPES)
    sent_at = models.DateTimeField(auto_now_add=True)
    
    # Email details
    subject = models.CharField(max_length=300)
    email_sent = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    
    # Context information
    days_before_due = models.IntegerField(
        null=True,
        blank=True,
        help_text="Days before due date when sent (negative for overdue)"
    )
    
    class Meta:
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['action', 'user', 'reminder_type']),
            models.Index(fields=['sent_at']),
        ]
        unique_together = [
            ('action', 'user', 'reminder_type', 'days_before_due'),
        ]

    def __str__(self):
        return f"{self.reminder_type} for {self.action.action_id} to {self.user.username}"