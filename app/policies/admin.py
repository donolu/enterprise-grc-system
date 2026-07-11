"""
Policy Repository Admin Interface

Professional admin interface for managing policies, versions, and acknowledgments.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count
from django.http import HttpResponse
import csv

from .models import (
    PolicyCategory, Policy, PolicyVersion,
    PolicyAcknowledgment, PolicyDistribution
)


@admin.register(PolicyCategory)
class PolicyCategoryAdmin(admin.ModelAdmin):
    """Admin interface for policy categories."""

    list_display = [
        'name', 'colored_name', 'policies_count', 'description_preview',
        'created_at'
    ]
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Category Information', {
            'fields': ('name', 'description', 'color')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def colored_name(self, obj):
        """Display category name with color indicator."""
        return format_html(
            '<span style="display: inline-block; width: 12px; height: 12px; '
            'background-color: {}; border-radius: 50%; margin-right: 8px;"></span>{}',
            obj.color,
            obj.name
        )
    colored_name.short_description = 'Color'

    def policies_count(self, obj):
        """Display count of policies in this category."""
        count = obj.policies.count()
        if count > 0:
            url = reverse('admin:policies_policy_changelist') + f'?category__id__exact={obj.id}'
            return format_html('<a href="{}">{} policies</a>', url, count)
        return '0 policies'
    policies_count.short_description = 'Policies'

    def description_preview(self, obj):
        """Display truncated description."""
        if obj.description:
            return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
        return '-'
    description_preview.short_description = 'Description'


class PolicyVersionInline(admin.TabularInline):
    """Inline admin for policy versions."""

    model = PolicyVersion
    extra = 0
    fields = [
        'version_number', 'is_active', 'is_published', 'document',
        'effective_date', 'created_at'
    ]
    readonly_fields = ['created_at']
    ordering = ['-version_number']


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    """Admin interface for policies."""

    list_display = [
        'policy_code', 'colored_title', 'category_display', 'status', 'status_display',
        'owner_display', 'current_version_display', 'review_status',
        'acknowledgment_stats', 'created_at'
    ]
    list_filter = [
        'status', 'policy_type', 'category', 'requires_acknowledgment',
        'created_at', 'next_review_date'
    ]
    search_fields = ['title', 'policy_code', 'category__name', 'owner__email']
    readonly_fields = [
        'policy_code', 'created_at', 'updated_at', 'current_version',
        'latest_version', 'is_due_for_review'
    ]
    list_editable = ['status']
    date_hierarchy = 'created_at'
    inlines = [PolicyVersionInline]

    fieldsets = (
        ('Policy Information', {
            'fields': (
                'policy_code', 'title', 'category', 'policy_type', 'status'
            )
        }),
        ('Management', {
            'fields': ('owner', 'approver')
        }),
        ('Review Schedule', {
            'fields': (
                'review_frequency_months', 'next_review_date', 'is_due_for_review'
            )
        }),
        ('Acknowledgment Settings', {
            'fields': (
                'requires_acknowledgment', 'acknowledgment_validity_days'
            )
        }),
        ('Version Information', {
            'fields': ('current_version', 'latest_version'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

    actions = [
        'mark_as_approved', 'mark_as_under_review', 'mark_as_draft',
        'export_policies_csv'
    ]

    def colored_title(self, obj):
        """Display title with category color."""
        return format_html(
            '<span style="border-left: 4px solid {}; padding-left: 8px;">{}</span>',
            obj.category.color,
            obj.title
        )
    colored_title.short_description = 'Title'

    def category_display(self, obj):
        """Display category with color indicator."""
        return format_html(
            '<span style="display: inline-block; width: 10px; height: 10px; '
            'background-color: {}; border-radius: 50%; margin-right: 6px;"></span>{}',
            obj.category.color,
            obj.category.name
        )
    category_display.short_description = 'Category'

    def status_display(self, obj):
        """Display status with color coding."""
        colors = {
            'draft': '#6b7280',      # gray
            'under_review': '#f59e0b', # amber
            'approved': '#10b981',    # emerald
            'archived': '#ef4444'     # red
        }

        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: 500;">{}</span>',
            colors.get(obj.status, '#6b7280'),
            obj.get_status_display()
        )
    status_display.short_description = 'Status'

    def owner_display(self, obj):
        """Display owner information."""
        return obj.owner.get_full_name() or obj.owner.email
    owner_display.short_description = 'Owner'

    def current_version_display(self, obj):
        """Display current version information."""
        current = obj.current_version
        if current:
            return format_html(
                '<span title="Active version">v{}</span>',
                current.version_number
            )
        return format_html('<span style="color: #ef4444;">No active version</span>')
    current_version_display.short_description = 'Current Version'

    def review_status(self, obj):
        """Display review status."""
        if obj.is_due_for_review:
            return format_html(
                '<span style="color: #ef4444; font-weight: 500;">📅 Due for review</span>'
            )
        elif obj.next_review_date:
            return format_html(
                '<span style="color: #10b981;">Next review: {}</span>',
                obj.next_review_date.strftime('%Y-%m-%d')
            )
        return 'No review scheduled'
    review_status.short_description = 'Review Status'

    def acknowledgment_stats(self, obj):
        """Display acknowledgment statistics."""
        current = obj.current_version
        if not current or not obj.requires_acknowledgment:
            return '-'

        total_acks = current.acknowledgments.count()
        total_dist = current.distributions.count()

        if total_dist == 0:
            return 'Not distributed'

        rate = (total_acks / total_dist) * 100
        color = '#10b981' if rate >= 80 else '#f59e0b' if rate >= 50 else '#ef4444'

        return format_html(
            '<span style="color: {}; font-weight: 500;">{}/{} ({:.0f}%)</span>',
            color, total_acks, total_dist, rate
        )
    acknowledgment_stats.short_description = 'Acknowledgments'

    def mark_as_approved(self, request, queryset):
        """Mark selected policies as approved."""
        updated = queryset.update(status='approved')
        self.message_user(request, f'{updated} policies marked as approved.')
    mark_as_approved.short_description = 'Mark as approved'

    def mark_as_under_review(self, request, queryset):
        """Mark selected policies as under review."""
        updated = queryset.update(status='under_review')
        self.message_user(request, f'{updated} policies marked as under review.')
    mark_as_under_review.short_description = 'Mark as under review'

    def mark_as_draft(self, request, queryset):
        """Mark selected policies as draft."""
        updated = queryset.update(status='draft')
        self.message_user(request, f'{updated} policies marked as draft.')
    mark_as_draft.short_description = 'Mark as draft'

    def export_policies_csv(self, request, queryset):
        """Export selected policies to CSV."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="policies.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Policy Code', 'Title', 'Category', 'Status', 'Owner',
            'Current Version', 'Next Review', 'Requires Acknowledgment',
            'Created Date'
        ])

        for policy in queryset:
            writer.writerow([
                policy.policy_code,
                policy.title,
                policy.category.name,
                policy.get_status_display(),
                policy.owner.email,
                policy.current_version.version_number if policy.current_version else 'None',
                policy.next_review_date,
                'Yes' if policy.requires_acknowledgment else 'No',
                policy.created_at.strftime('%Y-%m-%d %H:%M')
            ])

        return response
    export_policies_csv.short_description = 'Export selected policies to CSV'


@admin.register(PolicyVersion)
class PolicyVersionAdmin(admin.ModelAdmin):
    """Admin interface for policy versions."""

    list_display = [
        'policy_code', 'version_number', 'status_indicators',
        'document_info', 'effective_date', 'acknowledgment_count',
        'created_by_display', 'created_at'
    ]
    list_filter = [
        'is_active', 'is_published', 'policy__category',
        'created_at', 'effective_date'
    ]
    search_fields = [
        'policy__title', 'policy__policy_code', 'version_number', 'summary'
    ]
    readonly_fields = [
        'document_size', 'file_name', 'file_extension',
        'is_current', 'is_expired', 'created_at'
    ]
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Version Information', {
            'fields': (
                'policy', 'version_number', 'summary'
            )
        }),
        ('Document', {
            'fields': (
                'document', 'document_size', 'file_name', 'file_extension'
            )
        }),
        ('Status', {
            'fields': (
                'is_active', 'is_published', 'is_current', 'is_expired'
            )
        }),
        ('Dates', {
            'fields': (
                'effective_date', 'expiry_date'
            )
        }),
        ('Approval', {
            'fields': (
                'approved_at', 'approved_by'
            )
        }),
        ('Metadata', {
            'fields': (
                'created_at', 'created_by'
            ),
            'classes': ('collapse',)
        }),
    )

    actions = ['activate_versions', 'publish_versions', 'approve_versions']

    def policy_code(self, obj):
        """Display policy code with link."""
        url = reverse('admin:policies_policy_change', args=[obj.policy.id])
        return format_html('<a href="{}">{}</a>', url, obj.policy.policy_code)
    policy_code.short_description = 'Policy Code'

    def status_indicators(self, obj):
        """Display status indicators."""
        indicators = []

        if obj.is_active:
            indicators.append('<span style="color: #10b981; font-weight: 500;">🟢 Active</span>')
        if obj.is_published:
            indicators.append('<span style="color: #3b82f6;">📋 Published</span>')
        if obj.approved_at:
            indicators.append('<span style="color: #10b981;">✅ Approved</span>')

        return format_html(' '.join(indicators)) if indicators else '-'
    status_indicators.short_description = 'Status'

    def document_info(self, obj):
        """Display document information."""
        if obj.document:
            size_mb = obj.document_size / (1024 * 1024) if obj.document_size else 0
            return format_html(
                '{}<br><small style="color: #6b7280;">{:.1f} MB</small>',
                obj.file_name or 'Document',
                size_mb
            )
        return 'No document'
    document_info.short_description = 'Document'

    def acknowledgment_count(self, obj):
        """Display acknowledgment count."""
        count = obj.acknowledgments.count()
        if count > 0:
            url = reverse('admin:policies_policyacknowledgment_changelist') + f'?policy_version__id__exact={obj.id}'
            return format_html('<a href="{}">{} acks</a>', url, count)
        return '0'
    acknowledgment_count.short_description = 'Acknowledgments'

    def created_by_display(self, obj):
        """Display creator information."""
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return 'System'
    created_by_display.short_description = 'Created By'

    def activate_versions(self, request, queryset):
        """Activate selected versions."""
        count = 0
        for version in queryset:
            # Deactivate other versions of the same policy
            PolicyVersion.objects.filter(
                policy=version.policy,
                is_active=True
            ).update(is_active=False)

            # Activate this version
            version.is_active = True
            version.save()
            count += 1

        self.message_user(request, f'{count} versions activated.')
    activate_versions.short_description = 'Activate selected versions'

    def publish_versions(self, request, queryset):
        """Publish selected versions."""
        updated = queryset.update(is_published=True)
        self.message_user(request, f'{updated} versions published.')
    publish_versions.short_description = 'Publish selected versions'

    def approve_versions(self, request, queryset):
        """Approve selected versions."""
        count = 0
        for version in queryset.filter(approved_at__isnull=True):
            version.approved_at = timezone.now()
            version.approved_by = request.user
            version.save()
            count += 1

        self.message_user(request, f'{count} versions approved.')
    approve_versions.short_description = 'Approve selected versions'


@admin.register(PolicyAcknowledgment)
class PolicyAcknowledgmentAdmin(admin.ModelAdmin):
    """Admin interface for policy acknowledgments."""

    list_display = [
        'user_display', 'policy_info', 'acknowledged_at',
        'validity_status', 'ip_address'
    ]
    list_filter = [
        'acknowledged_at', 'policy_version__policy__category',
        'policy_version__policy__requires_acknowledgment'
    ]
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'policy_version__policy__title', 'policy_version__policy__policy_code'
    ]
    readonly_fields = [
        'acknowledged_at', 'is_expired', 'is_valid'
    ]
    date_hierarchy = 'acknowledged_at'

    fieldsets = (
        ('Acknowledgment Information', {
            'fields': (
                'user', 'policy_version', 'acknowledged_at'
            )
        }),
        ('Validity', {
            'fields': (
                'expires_at', 'is_expired', 'is_valid'
            )
        }),
        ('Metadata', {
            'fields': (
                'ip_address', 'user_agent'
            ),
            'classes': ('collapse',)
        }),
    )

    def user_display(self, obj):
        """Display user information."""
        return format_html(
            '{}<br><small style="color: #6b7280;">{}</small>',
            obj.user.get_full_name() or 'No name',
            obj.user.email
        )
    user_display.short_description = 'User'

    def policy_info(self, obj):
        """Display policy information."""
        policy_url = reverse('admin:policies_policy_change', args=[obj.policy_version.policy.id])
        return format_html(
            '<a href="{}">{}</a><br>'
            '<small style="color: #6b7280;">v{}</small>',
            policy_url,
            obj.policy_version.policy.title,
            obj.policy_version.version_number
        )
    policy_info.short_description = 'Policy'

    def validity_status(self, obj):
        """Display validity status."""
        if obj.is_expired:
            return format_html(
                '<span style="color: #ef4444; font-weight: 500;">❌ Expired</span>'
            )
        elif obj.expires_at:
            days_left = (obj.expires_at - timezone.now()).days
            if days_left <= 30:
                return format_html(
                    '<span style="color: #f59e0b; font-weight: 500;">⚠️ Expires in {} days</span>',
                    days_left
                )
            else:
                return format_html(
                    '<span style="color: #10b981;">✅ Valid ({} days left)</span>',
                    days_left
                )
        return format_html('<span style="color: #10b981;">✅ Valid (no expiry)</span>')
    validity_status.short_description = 'Status'


@admin.register(PolicyDistribution)
class PolicyDistributionAdmin(admin.ModelAdmin):
    """Admin interface for policy distributions."""

    list_display = [
        'user_display', 'policy_info', 'distributed_at',
        'status_display', 'reminder_info', 'distributed_by_display'
    ]
    list_filter = [
        'acknowledged', 'notification_sent', 'distributed_at',
        'policy_version__policy__category'
    ]
    search_fields = [
        'distributed_to__email', 'distributed_to__first_name', 'distributed_to__last_name',
        'policy_version__policy__title', 'policy_version__policy__policy_code'
    ]
    readonly_fields = [
        'distributed_at', 'notification_sent_at', 'acknowledged_at', 'is_overdue'
    ]
    date_hierarchy = 'distributed_at'

    fieldsets = (
        ('Distribution Information', {
            'fields': (
                'policy_version', 'distributed_to', 'distributed_by', 'distributed_at'
            )
        }),
        ('Status', {
            'fields': (
                'acknowledged', 'acknowledged_at', 'is_overdue'
            )
        }),
        ('Notifications', {
            'fields': (
                'notification_sent', 'notification_sent_at',
                'reminder_count', 'last_reminder_sent'
            )
        }),
    )

    actions = ['send_reminders', 'mark_as_acknowledged']

    def user_display(self, obj):
        """Display user information."""
        return format_html(
            '{}<br><small style="color: #6b7280;">{}</small>',
            obj.distributed_to.get_full_name() or 'No name',
            obj.distributed_to.email
        )
    user_display.short_description = 'User'

    def policy_info(self, obj):
        """Display policy information."""
        policy_url = reverse('admin:policies_policy_change', args=[obj.policy_version.policy.id])
        return format_html(
            '<a href="{}">{}</a><br>'
            '<small style="color: #6b7280;">v{}</small>',
            policy_url,
            obj.policy_version.policy.title,
            obj.policy_version.version_number
        )
    policy_info.short_description = 'Policy'

    def status_display(self, obj):
        """Display acknowledgment status."""
        if obj.acknowledged:
            return format_html(
                '<span style="color: #10b981; font-weight: 500;">✅ Acknowledged</span><br>'
                '<small style="color: #6b7280;">{}</small>',
                obj.acknowledged_at.strftime('%Y-%m-%d %H:%M') if obj.acknowledged_at else 'Unknown'
            )
        elif obj.is_overdue:
            return format_html(
                '<span style="color: #ef4444; font-weight: 500;">🚨 Overdue</span>'
            )
        else:
            return format_html(
                '<span style="color: #f59e0b; font-weight: 500;">⏳ Pending</span>'
            )
    status_display.short_description = 'Status'

    def reminder_info(self, obj):
        """Display reminder information."""
        if obj.reminder_count > 0:
            return format_html(
                '{} reminders<br>'
                '<small style="color: #6b7280;">Last: {}</small>',
                obj.reminder_count,
                obj.last_reminder_sent.strftime('%Y-%m-%d') if obj.last_reminder_sent else 'Unknown'
            )
        return 'No reminders'
    reminder_info.short_description = 'Reminders'

    def distributed_by_display(self, obj):
        """Display distributor information."""
        if obj.distributed_by:
            return obj.distributed_by.get_full_name() or obj.distributed_by.email
        return 'System'
    distributed_by_display.short_description = 'Distributed By'

    def send_reminders(self, request, queryset):
        """Send reminders for selected distributions."""
        pending = queryset.filter(acknowledged=False)
        count = pending.count()

        # Here you would implement the actual reminder sending logic
        # For now, just update the reminder count and timestamp
        for distribution in pending:
            distribution.reminder_count += 1
            distribution.last_reminder_sent = timezone.now()
            distribution.save()

        self.message_user(request, f'Reminders sent for {count} distributions.')
    send_reminders.short_description = 'Send reminders for selected distributions'

    def mark_as_acknowledged(self, request, queryset):
        """Mark selected distributions as acknowledged."""
        updated = queryset.filter(acknowledged=False).update(
            acknowledged=True,
            acknowledged_at=timezone.now()
        )
        self.message_user(request, f'{updated} distributions marked as acknowledged.')
    mark_as_acknowledged.short_description = 'Mark as acknowledged'