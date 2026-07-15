from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Asset, AssetReviewReminderLog


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = [
        'asset_id', 'name', 'asset_type', 'classification', 'criticality',
        'lifecycle_status', 'owner_display', 'location', 'next_review_date',
    ]
    list_filter = [
        'asset_type', 'classification', 'criticality', 'lifecycle_status',
        'next_review_date',
    ]
    search_fields = [
        'asset_id', 'name', 'description', 'owner_name', 'serial_number',
        'ip_address', 'mac_address', 'location',
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'source_path', 'source_sheet',
        'source_row', 'source_checksum', 'risk_count', 'control_count',
        'document_count',
    ]
    raw_id_fields = ['owner', 'created_by']
    filter_horizontal = ['linked_risks', 'linked_controls', 'linked_documents']

    fieldsets = (
        ('Identification', {
            'fields': ('asset_id', 'name', 'asset_type', 'description')
        }),
        ('Classification', {
            'fields': ('classification', 'criticality', 'lifecycle_status')
        }),
        ('Ownership', {
            'fields': ('owner', 'owner_name', 'custodian', 'location')
        }),
        ('Technical Details', {
            'fields': (
                'domain', 'ip_address', 'mac_address', 'serial_number',
                'manufacturer', 'model', 'operating_system', 'version',
            ),
            'classes': ('collapse',),
        }),
        ('Lifecycle Dates', {
            'fields': (
                'acquisition_date', 'last_seen_at', 'last_reviewed_at',
                'next_review_date', 'disposal_date',
            )
        }),
        ('Links', {
            'fields': (
                'linked_risks', 'risk_count', 'linked_controls',
                'control_count', 'linked_documents', 'document_count',
            )
        }),
        ('Import Metadata', {
            'fields': (
                'source_path', 'source_sheet', 'source_row',
                'source_checksum', 'metadata',
            ),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def owner_display(self, obj):
        if obj.owner:
            return obj.owner.get_full_name() or obj.owner.username
        return obj.owner_name

    def risk_count(self, obj):
        count = obj.linked_risks.count()
        if count:
            url = reverse('admin:risk_risk_changelist') + f'?linked_assets__id__exact={obj.id}'
            return format_html('<a href="{}">{} risks</a>', url, count)
        return '0 risks'

    def control_count(self, obj):
        count = obj.linked_controls.count()
        if count:
            url = reverse('admin:catalogs_control_changelist') + f'?linked_assets__id__exact={obj.id}'
            return format_html('<a href="{}">{} controls</a>', url, count)
        return '0 controls'

    def document_count(self, obj):
        count = obj.linked_documents.count()
        return f'{count} documents'


@admin.register(AssetReviewReminderLog)
class AssetReviewReminderLogAdmin(admin.ModelAdmin):
    list_display = ['asset', 'owner', 'reminder_type', 'review_date', 'sent_at', 'email_sent']
    list_filter = ['reminder_type', 'email_sent', 'review_date', 'sent_at']
    search_fields = ['asset__asset_id', 'asset__name', 'owner__username', 'owner__email']
    readonly_fields = ['asset', 'owner', 'reminder_type', 'review_date', 'sent_at', 'email_sent']
