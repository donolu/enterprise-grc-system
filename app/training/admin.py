"""
Training Admin Interface

Professional admin interface for security awareness training management.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils import timezone

from .models import (
    TrainingCategory,
    TrainingVideo,
    SecurityAwarenessCampaign,
    CampaignDelivery,
    VideoView
)


@admin.register(TrainingCategory)
class TrainingCategoryAdmin(admin.ModelAdmin):
    """Admin interface for training categories."""

    list_display = ['colored_name', 'description', 'videos_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']

    def colored_name(self, obj):
        """Display category name with color indicator."""
        return format_html(
            '<span style="display: inline-block; width: 12px; height: 12px; '
            'background-color: {}; border-radius: 50%; margin-right: 8px;"></span>{}',
            obj.color, obj.name
        )
    colored_name.short_description = 'Category'

    def videos_count(self, obj):
        """Display count of videos in this category."""
        count = obj.videos.filter(is_published=True).count()
        return format_html(
            '<span style="color: #1890ff; font-weight: bold;">{}</span> videos',
            count
        )
    videos_count.short_description = 'Published Videos'


@admin.register(TrainingVideo)
class TrainingVideoAdmin(admin.ModelAdmin):
    """Admin interface for training videos."""

    list_display = [
        'title', 'category_colored', 'video_provider', 'difficulty_colored',
        'duration_display', 'view_count', 'is_published', 'created_at'
    ]
    list_filter = [
        'is_published', 'video_provider', 'difficulty_level',
        'category', 'created_at'
    ]
    search_fields = ['title', 'description', 'category__name']
    ordering = ['-created_at']
    readonly_fields = ['view_count', 'created_at', 'updated_at', 'published_at']

    fieldsets = (
        ('Video Information', {
            'fields': ('title', 'description', 'category')
        }),
        ('Video Source', {
            'fields': ('video_provider', 'video_url', 'video_id')
        }),
        ('Content Details', {
            'fields': ('duration_minutes', 'difficulty_level')
        }),
        ('Publishing', {
            'fields': ('is_published', 'published_at')
        }),
        ('Statistics', {
            'fields': ('view_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    actions = ['publish_videos', 'unpublish_videos']

    def category_colored(self, obj):
        """Display category with color."""
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            obj.category.color, obj.category.name
        )
    category_colored.short_description = 'Category'

    def difficulty_colored(self, obj):
        """Display difficulty with color coding."""
        colors = {
            'beginner': '#52c41a',
            'intermediate': '#faad14',
            'advanced': '#f5222d'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.difficulty_level, '#666'),
            obj.get_difficulty_level_display()
        )
    difficulty_colored.short_description = 'Difficulty'

    def duration_display(self, obj):
        """Display formatted duration."""
        if not obj.duration_minutes:
            return format_html('<span style="color: #999;">Not specified</span>')

        if obj.duration_minutes < 60:
            return f"{obj.duration_minutes} min"

        hours = obj.duration_minutes // 60
        minutes = obj.duration_minutes % 60
        return f"{hours}h {minutes}m"
    duration_display.short_description = 'Duration'

    def publish_videos(self, request, queryset):
        """Bulk action to publish videos."""
        count = queryset.update(is_published=True, published_at=timezone.now())
        self.message_user(
            request,
            f"{count} video(s) have been published successfully.",
            messages.SUCCESS
        )
    publish_videos.short_description = "Publish selected videos"

    def unpublish_videos(self, request, queryset):
        """Bulk action to unpublish videos."""
        count = queryset.update(is_published=False)
        self.message_user(
            request,
            f"{count} video(s) have been unpublished.",
            messages.SUCCESS
        )
    unpublish_videos.short_description = "Unpublish selected videos"

    def save_model(self, request, obj, form, change):
        """Set created_by when creating new videos."""
        if not change:  # Creating new video
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SecurityAwarenessCampaign)
class SecurityAwarenessCampaignAdmin(admin.ModelAdmin):
    """Admin interface for security awareness campaigns."""

    list_display = [
        'name', 'status_colored', 'send_frequency', 'next_send_date',
        'target_audience', 'email_stats', 'created_at'
    ]
    list_filter = [
        'is_active', 'send_frequency', 'send_to_all_users',
        'start_date', 'created_at'
    ]
    search_fields = ['name', 'description', 'subject_line']
    ordering = ['-created_at']
    readonly_fields = [
        'total_sent', 'total_opened', 'total_clicked', 'open_rate', 'click_rate',
        'created_at', 'updated_at'
    ]

    fieldsets = (
        ('Campaign Information', {
            'fields': ('name', 'description')
        }),
        ('Email Content', {
            'fields': ('subject_line', 'email_content')
        }),
        ('Scheduling', {
            'fields': ('is_active', 'send_frequency', 'start_date', 'end_date', 'next_send_date')
        }),
        ('Target Audience', {
            'fields': ('send_to_all_users', 'target_users')
        }),
        ('Statistics', {
            'fields': (
                'total_sent', 'total_opened', 'total_clicked',
                'open_rate', 'click_rate'
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    actions = ['activate_campaigns', 'deactivate_campaigns', 'send_test_emails']

    def status_colored(self, obj):
        """Display campaign status with color coding."""
        now = timezone.now()

        if not obj.is_active:
            return format_html(
                '<span style="color: #999; font-weight: bold;">Inactive</span>'
            )
        elif obj.end_date and obj.end_date < now:
            return format_html(
                '<span style="color: #666; font-weight: bold;">Ended</span>'
            )
        elif obj.start_date > now:
            return format_html(
                '<span style="color: #faad14; font-weight: bold;">Scheduled</span>'
            )
        elif obj.next_send_date <= now:
            return format_html(
                '<span style="color: #f5222d; font-weight: bold;">Ready to Send</span>'
            )
        else:
            return format_html(
                '<span style="color: #52c41a; font-weight: bold;">Active</span>'
            )
    status_colored.short_description = 'Status'

    def target_audience(self, obj):
        """Display target audience information."""
        if obj.send_to_all_users:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            count = User.objects.filter(is_active=True).count()
            return format_html(
                '<span style="color: #1890ff;">All Users</span> ({})',
                count
            )
        else:
            count = obj.target_users.count()
            return format_html(
                '<span style="color: #722ed1;">Specific Users</span> ({})',
                count
            )
    target_audience.short_description = 'Audience'

    def email_stats(self, obj):
        """Display email statistics."""
        if obj.total_sent == 0:
            return format_html('<span style="color: #999;">No emails sent</span>')

        return format_html(
            '<strong>{}</strong> sent<br>'
            '<span style="color: #52c41a;">{}%</span> opened<br>'
            '<span style="color: #1890ff;">{}%</span> clicked',
            obj.total_sent,
            round(obj.open_rate, 1),
            round(obj.click_rate, 1)
        )
    email_stats.short_description = 'Email Stats'

    def activate_campaigns(self, request, queryset):
        """Bulk action to activate campaigns."""
        count = queryset.update(is_active=True)
        self.message_user(
            request,
            f"{count} campaign(s) have been activated.",
            messages.SUCCESS
        )
    activate_campaigns.short_description = "Activate selected campaigns"

    def deactivate_campaigns(self, request, queryset):
        """Bulk action to deactivate campaigns."""
        count = queryset.update(is_active=False)
        self.message_user(
            request,
            f"{count} campaign(s) have been deactivated.",
            messages.SUCCESS
        )
    deactivate_campaigns.short_description = "Deactivate selected campaigns"

    def send_test_emails(self, request, queryset):
        """Send test emails for selected campaigns."""
        from .tasks import send_test_awareness_email

        sent_count = 0
        for campaign in queryset:
            try:
                send_test_awareness_email.delay(str(campaign.id), str(request.user.id))
                sent_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Failed to send test email for {campaign.name}: {e}",
                    messages.ERROR
                )

        if sent_count > 0:
            self.message_user(
                request,
                f"Test emails queued for {sent_count} campaign(s). Check your email.",
                messages.SUCCESS
            )
    send_test_emails.short_description = "Send test emails to yourself"

    def save_model(self, request, obj, form, change):
        """Set created_by when creating new campaigns."""
        if not change:  # Creating new campaign
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CampaignDelivery)
class CampaignDeliveryAdmin(admin.ModelAdmin):
    """Admin interface for campaign deliveries."""

    list_display = [
        'campaign_name', 'user_email', 'status_colored',
        'sent_at', 'opened_at', 'clicked_at'
    ]
    list_filter = [
        'delivery_status', 'campaign', 'sent_at', 'opened_at', 'clicked_at'
    ]
    search_fields = [
        'campaign__name', 'user__email', 'recipient_email', 'email_subject'
    ]
    ordering = ['-sent_at']
    readonly_fields = ['sent_at']

    def campaign_name(self, obj):
        """Display campaign name as link."""
        url = reverse('admin:training_securityawarenesscampaign_change', args=[obj.campaign.id])
        return format_html('<a href="{}">{}</a>', url, obj.campaign.name)
    campaign_name.short_description = 'Campaign'

    def user_email(self, obj):
        """Display user email with name if available."""
        if obj.user.first_name or obj.user.last_name:
            name = f"{obj.user.first_name} {obj.user.last_name}".strip()
            return f"{name} ({obj.user.email})"
        return obj.user.email
    user_email.short_description = 'Recipient'

    def status_colored(self, obj):
        """Display delivery status with color coding."""
        colors = {
            'sent': '#666',
            'delivered': '#1890ff',
            'opened': '#52c41a',
            'clicked': '#722ed1',
            'bounced': '#faad14',
            'failed': '#f5222d'
        }

        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.delivery_status, '#666'),
            obj.get_delivery_status_display()
        )
    status_colored.short_description = 'Status'


@admin.register(VideoView)
class VideoViewAdmin(admin.ModelAdmin):
    """Admin interface for video views."""

    list_display = [
        'video_title', 'user_email', 'completion_colored',
        'duration_watched', 'started_at'
    ]
    list_filter = [
        'completed', 'video__category', 'started_at'
    ]
    search_fields = [
        'video__title', 'user__email'
    ]
    ordering = ['-started_at']
    readonly_fields = ['started_at']

    def video_title(self, obj):
        """Display video title as link."""
        url = reverse('admin:training_trainingvideo_change', args=[obj.video.id])
        return format_html('<a href="{}">{}</a>', url, obj.video.title)
    video_title.short_description = 'Video'

    def user_email(self, obj):
        """Display user email with name if available."""
        if obj.user.first_name or obj.user.last_name:
            name = f"{obj.user.first_name} {obj.user.last_name}".strip()
            return f"{name} ({obj.user.email})"
        return obj.user.email
    user_email.short_description = 'User'

    def completion_colored(self, obj):
        """Display completion percentage with color coding."""
        if obj.completed:
            return format_html(
                '<span style="color: #52c41a; font-weight: bold;">{}%</span> ✓',
                obj.completion_percentage
            )
        elif obj.completion_percentage >= 50:
            return format_html(
                '<span style="color: #faad14; font-weight: bold;">{}%</span>',
                obj.completion_percentage
            )
        else:
            return format_html(
                '<span style="color: #f5222d;">{}%</span>',
                obj.completion_percentage
            )
    completion_colored.short_description = 'Completion'


# Customize admin site headers
admin.site.site_header = "GRC Training Administration"
admin.site.site_title = "GRC Training Admin"
admin.site.index_title = "Security Awareness Training Management"