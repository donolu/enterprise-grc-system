import hashlib
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class ScanTarget(models.Model):
    TARGET_TYPES = [
        ('web', 'Web application'),
        ('host', 'Host'),
        ('api', 'API endpoint'),
    ]

    STATUS_CHOICES = [
        ('pending_approval', 'Pending approval'),
        ('approved', 'Approved'),
        ('disabled', 'Disabled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    target_type = models.CharField(max_length=20, choices=TARGET_TYPES, default='web')
    address = models.CharField(max_length=500)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending_approval')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_scan_targets',
    )
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_scan_targets',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['status', 'target_type']),
            models.Index(fields=['owner']),
            models.Index(fields=['address']),
        ]

    def __str__(self):
        return f'{self.name} ({self.address})'


class ScanSchedule(models.Model):
    FREQUENCY_CHOICES = [
        ('manual', 'Manual'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target = models.ForeignKey(ScanTarget, on_delete=models.CASCADE, related_name='schedules')
    name = models.CharField(max_length=255)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='manual')
    is_active = models.BooleanField(default=True)
    next_run_at = models.DateTimeField(null=True, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_scan_schedules',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['next_run_at', 'name']
        indexes = [
            models.Index(fields=['target', 'is_active']),
            models.Index(fields=['next_run_at', 'is_active']),
        ]

    def __str__(self):
        return f'{self.name} for {self.target.name}'


class ScanJob(models.Model):
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    SCANNER_CHOICES = [
        ('nuclei', 'Nuclei'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target = models.ForeignKey(ScanTarget, on_delete=models.CASCADE, related_name='scan_jobs')
    schedule = models.ForeignKey(
        ScanSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scan_jobs',
    )
    scanner = models.CharField(max_length=30, choices=SCANNER_CHOICES, default='nuclei')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requested_scan_jobs',
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    findings_count = models.PositiveIntegerField(default=0)
    scan_config = models.JSONField(default=dict, blank=True)
    raw_summary = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['target', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f'{self.scanner} scan for {self.target.name} ({self.status})'


class VulnerabilityFinding(models.Model):
    SEVERITY_CHOICES = [
        ('critical', 'Critical'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
        ('info', 'Info'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('accepted_risk', 'Accepted risk'),
        ('remediated', 'Remediated'),
        ('false_positive', 'False positive'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target = models.ForeignKey(ScanTarget, on_delete=models.CASCADE, related_name='findings')
    job = models.ForeignKey(ScanJob, on_delete=models.CASCADE, related_name='findings')
    fingerprint = models.CharField(max_length=64)
    scanner_name = models.CharField(max_length=50, default='nuclei')
    scanner_finding_id = models.CharField(max_length=255, blank=True)
    template_id = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='info')
    description = models.TextField(blank=True)
    remediation = models.TextField(blank=True)
    matched_at = models.CharField(max_length=500, blank=True)
    cve = models.CharField(max_length=80, blank=True)
    cvss_score = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    evidence = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='open')
    risk = models.ForeignKey(
        'risk.Risk',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vulnerability_findings',
    )
    risk_action = models.ForeignKey(
        'risk.RiskAction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vulnerability_findings',
    )
    first_seen_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['severity', '-last_seen_at']
        unique_together = [('target', 'fingerprint')]
        indexes = [
            models.Index(fields=['target', 'status']),
            models.Index(fields=['severity', 'status']),
            models.Index(fields=['scanner_finding_id']),
            models.Index(fields=['last_seen_at']),
        ]

    def __str__(self):
        return f'{self.severity}: {self.title}'

    @staticmethod
    def make_fingerprint(scanner_name, scanner_finding_id, matched_at, title):
        raw = '|'.join([scanner_name or '', scanner_finding_id or '', matched_at or '', title or ''])
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()
