import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class CalendarEvent(models.Model):
    EVENT_TYPES = [
        ('deadline', 'Deadline'),
        ('review', 'Review'),
        ('meeting', 'Meeting'),
        ('training', 'Training'),
        ('custom', 'Custom'),
    ]

    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES, default='deadline')
    due_date = models.DateField()
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='calendar_events',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    source_url = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_calendar_events',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date', 'title']
        indexes = [
            models.Index(fields=['due_date', 'status']),
            models.Index(fields=['owner', 'due_date']),
            models.Index(fields=['event_type']),
        ]

    def __str__(self):
        return f'{self.title} ({self.due_date})'


class CalendarNotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='calendar_notification_preference',
    )
    email_enabled = models.BooleanField(default=True)
    advance_reminder_days = models.PositiveIntegerField(default=7)
    due_date_enabled = models.BooleanField(default=True)
    overdue_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Calendar notification preferences for {self.user}'


class CalendarReminderLog(models.Model):
    REMINDER_TYPES = [
        ('advance_warning', 'Advance warning'),
        ('due_today', 'Due today'),
        ('overdue', 'Overdue'),
    ]

    source_type = models.CharField(max_length=50)
    source_id = models.CharField(max_length=80)
    title = models.CharField(max_length=255)
    due_date = models.DateField()
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='calendar_reminder_logs',
    )
    reminder_type = models.CharField(max_length=30, choices=REMINDER_TYPES)
    sent_at = models.DateTimeField(default=timezone.now)
    email_sent = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-sent_at']
        unique_together = [
            ('source_type', 'source_id', 'recipient', 'due_date', 'reminder_type'),
        ]
        indexes = [
            models.Index(fields=['source_type', 'source_id']),
            models.Index(fields=['recipient', 'sent_at']),
            models.Index(fields=['due_date', 'reminder_type']),
        ]

    def __str__(self):
        return f'{self.reminder_type} for {self.source_type}:{self.source_id}'


class CalendarAuditLog(models.Model):
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('deleted', 'Deleted'),
        ('reminder_sent', 'Reminder sent'),
    ]

    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    event = models.ForeignKey(
        CalendarEvent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
    )
    source_type = models.CharField(max_length=50, blank=True)
    source_id = models.CharField(max_length=80, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='calendar_audit_logs',
    )
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['source_type', 'source_id']),
        ]
