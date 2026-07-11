"""
Training Models

Security awareness training and email campaign management.
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import URLValidator
from datetime import timedelta

User = get_user_model()


class TrainingCategory(models.Model):
    """
    Categories for organizing training content.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(
        max_length=7,
        default="#1890ff",
        help_text="Hex color code for category display"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Training Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class TrainingVideo(models.Model):
    """
    Training videos from Synthesia.io or other providers.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        TrainingCategory,
        on_delete=models.CASCADE,
        related_name='videos'
    )

    # Video source information
    video_provider = models.CharField(
        max_length=50,
        choices=[
            ('synthesia', 'Synthesia.io'),
            ('youtube', 'YouTube'),
            ('vimeo', 'Vimeo'),
            ('custom', 'Custom URL')
        ],
        default='synthesia'
    )
    video_url = models.URLField(
        help_text="Full URL to the video or embed URL"
    )
    video_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Provider-specific video ID"
    )

    # Content metadata
    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Video duration in minutes"
    )
    difficulty_level = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced')
        ],
        default='beginner'
    )

    # Content management
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_training_videos'
    )

    # Tracking
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def embed_url(self):
        """Generate embed URL based on provider."""
        if self.video_provider == 'youtube' and self.video_id:
            return f"https://www.youtube.com/embed/{self.video_id}"
        elif self.video_provider == 'vimeo' and self.video_id:
            return f"https://player.vimeo.com/video/{self.video_id}"
        elif self.video_provider == 'synthesia':
            # Synthesia.io embed format (may need adjustment based on their API)
            return self.video_url
        else:
            return self.video_url


class SecurityAwarenessCampaign(models.Model):
    """
    Email campaigns for security awareness content.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Campaign content
    subject_line = models.CharField(max_length=200)
    email_content = models.TextField(
        help_text="HTML content for the email. Use {{user.first_name}} for personalization."
    )

    # Campaign settings
    is_active = models.BooleanField(default=True)
    send_frequency = models.CharField(
        max_length=20,
        choices=[
            ('weekly', 'Weekly'),
            ('biweekly', 'Bi-weekly'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
        ],
        default='monthly'
    )

    # Scheduling
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    next_send_date = models.DateTimeField()

    # Target audience
    send_to_all_users = models.BooleanField(
        default=True,
        help_text="If False, only send to specific users or groups"
    )
    target_users = models.ManyToManyField(
        User,
        blank=True,
        related_name='awareness_campaigns',
        help_text="Specific users to receive this campaign (if not sending to all)"
    )

    # Campaign management
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_campaigns'
    )
    total_sent = models.PositiveIntegerField(default=0)
    total_opened = models.PositiveIntegerField(default=0)
    total_clicked = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Set initial next_send_date if not set
        if not self.next_send_date and self.start_date:
            self.next_send_date = self.start_date
        super().save(*args, **kwargs)

    @property
    def open_rate(self):
        """Calculate email open rate percentage."""
        if self.total_sent == 0:
            return 0.0
        return (self.total_opened / self.total_sent) * 100

    @property
    def click_rate(self):
        """Calculate email click rate percentage."""
        if self.total_sent == 0:
            return 0.0
        return (self.total_clicked / self.total_sent) * 100

    def calculate_next_send_date(self):
        """Calculate the next send date based on frequency."""
        if not self.next_send_date:
            return None

        if self.send_frequency == 'weekly':
            return self.next_send_date + timedelta(weeks=1)
        elif self.send_frequency == 'biweekly':
            return self.next_send_date + timedelta(weeks=2)
        elif self.send_frequency == 'monthly':
            return self.next_send_date + timedelta(days=30)
        elif self.send_frequency == 'quarterly':
            return self.next_send_date + timedelta(days=90)

        return None

    def is_due_to_send(self):
        """Check if campaign is due to send."""
        if not self.is_active or not self.next_send_date:
            return False

        if self.end_date and timezone.now() > self.end_date:
            return False

        return timezone.now() >= self.next_send_date


class CampaignDelivery(models.Model):
    """
    Track individual email deliveries for campaigns.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        SecurityAwarenessCampaign,
        on_delete=models.CASCADE,
        related_name='deliveries'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='campaign_deliveries'
    )

    # Delivery tracking
    sent_at = models.DateTimeField(auto_now_add=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)

    # Email metadata
    email_subject = models.CharField(max_length=200)
    recipient_email = models.EmailField()
    delivery_status = models.CharField(
        max_length=20,
        choices=[
            ('sent', 'Sent'),
            ('delivered', 'Delivered'),
            ('opened', 'Opened'),
            ('clicked', 'Clicked'),
            ('bounced', 'Bounced'),
            ('failed', 'Failed')
        ],
        default='sent'
    )

    class Meta:
        unique_together = ['campaign', 'user', 'sent_at']
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.campaign.name} → {self.user.email}"


class VideoView(models.Model):
    """
    Track video views for analytics.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    video = models.ForeignKey(
        TrainingVideo,
        on_delete=models.CASCADE,
        related_name='views'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='video_views'
    )

    # View tracking
    started_at = models.DateTimeField(auto_now_add=True)
    duration_watched = models.PositiveIntegerField(
        default=0,
        help_text="Duration watched in seconds"
    )
    completed = models.BooleanField(
        default=False,
        help_text="Whether the user watched the full video"
    )
    completion_percentage = models.PositiveIntegerField(
        default=0,
        help_text="Percentage of video watched"
    )

    # Session information
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.user.email} watched {self.video.title} ({self.completion_percentage}%)"