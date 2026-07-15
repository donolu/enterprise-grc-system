from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class GovernanceArtefact(models.Model):
    ARTEFACT_TYPES = [
        ('scope_document', 'Scope Document'),
        ('metrics_pack', 'Metrics Pack'),
        ('agenda', 'Agenda'),
        ('management_review_pack', 'Management Review Pack'),
        ('regulatory_contractual_sheet', 'Regulatory and Contractual Sheet'),
        ('nonconformity_log', 'Non-Conformity Log'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]

    artefact_id = models.CharField(max_length=80, unique=True)
    title = models.CharField(max_length=255)
    artefact_type = models.CharField(max_length=40, choices=ARTEFACT_TYPES)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    version = models.CharField(max_length=30, default='1.0')

    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_governance_artefacts',
    )
    effective_date = models.DateField(null=True, blank=True)
    review_due_date = models.DateField(null=True, blank=True)

    linked_frameworks = models.ManyToManyField(
        'catalogs.Framework',
        blank=True,
        related_name='governance_artefacts',
    )
    linked_controls = models.ManyToManyField(
        'catalogs.Control',
        blank=True,
        related_name='governance_artefacts',
    )
    linked_documents = models.ManyToManyField(
        'core.Document',
        blank=True,
        related_name='governance_artefacts',
    )
    source_template = models.ForeignKey(
        'catalogs.TemplateDocument',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='governance_artefacts',
    )

    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_governance_artefacts',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['artefact_type', 'title']
        indexes = [
            models.Index(fields=['artefact_type', 'status']),
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['review_due_date']),
        ]

    def __str__(self):
        return f'{self.artefact_id}: {self.title}'

    def save(self, *args, **kwargs):
        if not self.artefact_id:
            self.artefact_id = self._generate_identifier('GOV')
        super().save(*args, **kwargs)

    @classmethod
    def _generate_identifier(cls, prefix):
        year = timezone.now().year
        existing_count = cls.objects.filter(artefact_id__startswith=f'{prefix}-{year}').count()
        return f'{prefix}-{year}-{existing_count + 1:04d}'


class RegulatoryRequirement(models.Model):
    SOURCE_TYPES = [
        ('regulation', 'Regulation'),
        ('contract', 'Contract'),
        ('standard', 'Standard'),
        ('policy', 'Policy'),
        ('other', 'Other'),
    ]

    APPLICABILITY_CHOICES = [
        ('under_review', 'Under Review'),
        ('applicable', 'Applicable'),
        ('not_applicable', 'Not Applicable'),
    ]

    COMPLIANCE_STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('compliant', 'Compliant'),
        ('non_compliant', 'Non-Compliant'),
        ('accepted_risk', 'Accepted Risk'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    requirement_id = models.CharField(max_length=80, unique=True)
    title = models.CharField(max_length=255)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    issuing_body = models.CharField(max_length=255, blank=True)
    jurisdiction = models.CharField(max_length=120, blank=True)
    reference = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)

    applicability_status = models.CharField(
        max_length=20,
        choices=APPLICABILITY_CHOICES,
        default='under_review',
    )
    compliance_status = models.CharField(
        max_length=20,
        choices=COMPLIANCE_STATUS_CHOICES,
        default='not_started',
    )
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')

    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_regulatory_requirements',
    )
    next_review_date = models.DateField(null=True, blank=True)

    linked_frameworks = models.ManyToManyField(
        'catalogs.Framework',
        blank=True,
        related_name='regulatory_requirements',
    )
    linked_controls = models.ManyToManyField(
        'catalogs.Control',
        blank=True,
        related_name='regulatory_requirements',
    )
    linked_risks = models.ManyToManyField(
        'risk.Risk',
        blank=True,
        related_name='regulatory_requirements',
    )
    linked_documents = models.ManyToManyField(
        'core.Document',
        blank=True,
        related_name='regulatory_requirements',
    )
    linked_artefacts = models.ManyToManyField(
        GovernanceArtefact,
        blank=True,
        related_name='regulatory_requirements',
    )

    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_regulatory_requirements',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['priority', 'title']
        indexes = [
            models.Index(fields=['source_type', 'applicability_status']),
            models.Index(fields=['compliance_status', 'priority']),
            models.Index(fields=['owner', 'compliance_status']),
            models.Index(fields=['next_review_date']),
        ]

    def __str__(self):
        return f'{self.requirement_id}: {self.title}'

    def save(self, *args, **kwargs):
        if not self.requirement_id:
            year = timezone.now().year
            existing_count = RegulatoryRequirement.objects.filter(
                requirement_id__startswith=f'REQ-{year}'
            ).count()
            self.requirement_id = f'REQ-{year}-{existing_count + 1:04d}'
        super().save(*args, **kwargs)


class NonConformity(models.Model):
    SEVERITY_CHOICES = [
        ('minor', 'Minor'),
        ('major', 'Major'),
        ('critical', 'Critical'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('root_cause_review', 'Root Cause Review'),
        ('corrective_action', 'Corrective Action'),
        ('verification', 'Verification'),
        ('closed', 'Closed'),
        ('accepted', 'Accepted'),
    ]

    SOURCE_TYPES = [
        ('internal_audit', 'Internal Audit'),
        ('external_audit', 'External Audit'),
        ('assessment', 'Assessment'),
        ('incident', 'Incident'),
        ('management_review', 'Management Review'),
        ('vendor_review', 'Vendor Review'),
        ('other', 'Other'),
    ]

    nonconformity_id = models.CharField(max_length=80, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='minor')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='open')
    source_type = models.CharField(max_length=30, choices=SOURCE_TYPES, default='assessment')

    detected_on = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    closed_on = models.DateField(null=True, blank=True)

    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_nonconformities',
    )
    raised_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='raised_nonconformities',
    )
    regulatory_requirement = models.ForeignKey(
        RegulatoryRequirement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='nonconformities',
    )

    root_cause = models.TextField(blank=True)
    corrective_action = models.TextField(blank=True)
    preventive_action = models.TextField(blank=True)
    verification_notes = models.TextField(blank=True)

    linked_controls = models.ManyToManyField(
        'catalogs.Control',
        blank=True,
        related_name='nonconformities',
    )
    linked_risks = models.ManyToManyField(
        'risk.Risk',
        blank=True,
        related_name='nonconformities',
    )
    linked_documents = models.ManyToManyField(
        'core.Document',
        blank=True,
        related_name='nonconformities',
    )

    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Non-conformities'
        ordering = ['-detected_on', 'severity', 'title']
        indexes = [
            models.Index(fields=['status', 'severity']),
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['source_type']),
        ]

    def __str__(self):
        return f'{self.nonconformity_id}: {self.title}'

    def save(self, *args, **kwargs):
        if not self.nonconformity_id:
            year = timezone.now().year
            existing_count = NonConformity.objects.filter(
                nonconformity_id__startswith=f'NC-{year}'
            ).count()
            self.nonconformity_id = f'NC-{year}-{existing_count + 1:04d}'
        if self.status in {'closed', 'accepted'} and not self.closed_on:
            self.closed_on = timezone.now().date()
        elif self.status not in {'closed', 'accepted'}:
            self.closed_on = None
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        return bool(self.due_date and self.status not in {'closed', 'accepted'} and self.due_date < timezone.now().date())


class ManagementReview(models.Model):
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('held', 'Held'),
        ('actions_open', 'Actions Open'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ]

    review_id = models.CharField(max_length=80, unique=True)
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    meeting_date = models.DateField()
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)

    chair = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chaired_management_reviews',
    )
    attendees = models.ManyToManyField(
        User,
        blank=True,
        related_name='management_review_attendances',
    )

    agenda = models.TextField(blank=True)
    minutes = models.TextField(blank=True)
    decisions = models.TextField(blank=True)
    actions_summary = models.TextField(blank=True)
    inputs = models.JSONField(default=dict, blank=True)
    outputs = models.JSONField(default=dict, blank=True)

    linked_requirements = models.ManyToManyField(
        RegulatoryRequirement,
        blank=True,
        related_name='management_reviews',
    )
    linked_nonconformities = models.ManyToManyField(
        NonConformity,
        blank=True,
        related_name='management_reviews',
    )
    linked_artefacts = models.ManyToManyField(
        GovernanceArtefact,
        blank=True,
        related_name='management_reviews',
    )
    linked_controls = models.ManyToManyField(
        'catalogs.Control',
        blank=True,
        related_name='management_reviews',
    )
    linked_documents = models.ManyToManyField(
        'core.Document',
        blank=True,
        related_name='management_reviews',
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_management_reviews',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-meeting_date', 'title']
        indexes = [
            models.Index(fields=['status', 'meeting_date']),
            models.Index(fields=['chair', 'status']),
        ]

    def __str__(self):
        return f'{self.review_id}: {self.title}'

    def save(self, *args, **kwargs):
        if not self.review_id:
            year = timezone.now().year
            existing_count = ManagementReview.objects.filter(
                review_id__startswith=f'MR-{year}'
            ).count()
            self.review_id = f'MR-{year}-{existing_count + 1:04d}'
        super().save(*args, **kwargs)
