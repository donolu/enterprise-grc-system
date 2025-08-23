"""
Vendor Management Admin Interface

Professional Django admin interface for vendor management with enhanced
features, bulk operations, and visual indicators for better user experience.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.db.models import Count
from .models import (
    RegionalConfig, VendorCategory, Vendor, VendorContact, 
    VendorService, VendorNote, VendorTask
)


@admin.register(RegionalConfig)
class RegionalConfigAdmin(admin.ModelAdmin):
    """Admin interface for regional configurations."""
    
    list_display = [
        'region_code', 'region_name', 'is_active',
        'compliance_standards_count', 'custom_fields_count', 'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['region_code', 'region_name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('region_code', 'region_name', 'description', 'is_active')
        }),
        ('Field Requirements', {
            'fields': ('required_fields', 'custom_fields'),
            'classes': ('collapse',)
        }),
        ('Compliance & Standards', {
            'fields': ('compliance_standards', 'validation_rules'),
            'classes': ('collapse',)
        }),
        ('Data Processing', {
            'fields': ('data_processing_requirements', 'contract_requirements'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def compliance_standards_count(self, obj):
        """Display count of compliance standards."""
        return len(obj.compliance_standards)
    compliance_standards_count.short_description = 'Standards Count'
    
    def custom_fields_count(self, obj):
        """Display count of custom fields."""
        return len(obj.custom_fields)
    custom_fields_count.short_description = 'Custom Fields Count'


@admin.register(VendorCategory)
class VendorCategoryAdmin(admin.ModelAdmin):
    """Admin interface for vendor categories."""
    
    list_display = [
        'name', 'colored_name', 'risk_weight', 'vendor_count', 
        'compliance_requirements_count', 'created_at'
    ]
    list_filter = ['risk_weight', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    def colored_name(self, obj):
        """Display category name with color indicator."""
        return format_html(
            '<span style="color: {}; font-weight: bold;">● {}</span>',
            obj.color_code,
            obj.name
        )
    colored_name.short_description = 'Category'
    
    def vendor_count(self, obj):
        """Display number of vendors in this category."""
        count = obj.vendor_set.count()
        url = reverse('admin:vendors_vendor_changelist') + f'?category__id__exact={obj.id}'
        return format_html('<a href="{}">{} vendor{}</a>', url, count, 's' if count != 1 else '')
    vendor_count.short_description = 'Vendors'
    
    def compliance_requirements_count(self, obj):
        """Display count of compliance requirements."""
        return len(obj.compliance_requirements)
    compliance_requirements_count.short_description = 'Requirements'


class VendorContactInline(admin.TabularInline):
    """Inline admin for vendor contacts."""
    model = VendorContact
    extra = 1
    fields = [
        'first_name', 'last_name', 'title', 'email', 'phone', 
        'contact_type', 'is_primary', 'is_active'
    ]
    readonly_fields = []


class VendorServiceInline(admin.TabularInline):
    """Inline admin for vendor services."""
    model = VendorService
    extra = 1
    fields = [
        'name', 'category', 'data_classification', 'cost_per_unit',
        'billing_frequency', 'is_active'
    ]
    readonly_fields = []


class VendorNoteInline(admin.TabularInline):
    """Inline admin for vendor notes."""
    model = VendorNote
    extra = 0
    fields = ['note_type', 'title', 'content', 'is_internal']
    readonly_fields = ['created_at', 'created_by']
    
    def get_queryset(self, request):
        """Limit to recent notes in inline."""
        qs = super().get_queryset(request)
        return qs.order_by('-created_at')[:5]


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    """Comprehensive admin interface for vendors."""
    
    list_display = [
        'vendor_id', 'name', 'colored_category', 'colored_status', 
        'colored_risk_level', 'assigned_to_link', 'contract_status',
        'performance_indicator', 'contact_count', 'service_count', 'created_at'
    ]
    list_filter = [
        'status', 'vendor_type', 'risk_level', 'category', 'assigned_to',
        'data_processing_agreement', 'security_assessment_completed',
        'auto_renewal', 'created_at'
    ]
    search_fields = [
        'vendor_id', 'name', 'legal_name', 'business_description', 
        'website', 'tax_id', 'duns_number'
    ]
    readonly_fields = [
        'vendor_id', 'full_address', 'is_contract_expiring_soon',
        'days_until_contract_expiry', 'created_at', 'updated_at', 'created_by'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                ('vendor_id', 'name', 'legal_name'),
                ('category', 'vendor_type', 'status'),
                'business_description',
                'website'
            )
        }),
        ('Business Details', {
            'fields': (
                ('tax_id', 'duns_number'),
                ('credit_rating', 'payment_terms'),
                'annual_spend'
            )
        }),
        ('Address', {
            'fields': (
                ('address_line1', 'address_line2'),
                ('city', 'state_province', 'postal_code'),
                'country',
                'full_address'
            ),
            'classes': ('collapse',)
        }),
        ('Regional Configuration', {
            'fields': (
                ('primary_region', 'operating_regions'),
                'custom_fields'
            ),
            'classes': ('collapse',)
        }),
        ('Risk Assessment', {
            'fields': (
                ('risk_level', 'risk_score'),
                ('performance_score', 'last_performance_review')
            )
        }),
        ('Compliance', {
            'fields': (
                ('data_processing_agreement', 'security_assessment_completed'),
                'security_assessment_date',
                'certifications',
                'compliance_status'
            ),
            'classes': ('collapse',)
        }),
        ('Contract Information', {
            'fields': (
                ('primary_contract_number', 'auto_renewal'),
                ('contract_start_date', 'contract_end_date'),
                ('renewal_notice_days', 'is_contract_expiring_soon'),
                'days_until_contract_expiry'
            ),
            'classes': ('collapse',)
        }),
        ('Relationship Management', {
            'fields': (
                ('assigned_to', 'relationship_start_date'),
                'notes',
                'tags'
            )
        }),
        ('Metadata', {
            'fields': (
                ('created_at', 'updated_at'),
                'created_by'
            ),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [VendorContactInline, VendorServiceInline, VendorNoteInline]
    
    actions = [
        'mark_active', 'mark_inactive', 'mark_approved',
        'send_renewal_reminders', 'bulk_assign_user', 'export_vendor_data'
    ]
    
    def get_queryset(self, request):
        """Optimize queryset with related objects."""
        return super().get_queryset(request).select_related(
            'category', 'assigned_to', 'created_by'
        ).prefetch_related('contacts', 'services')
    
    def colored_category(self, obj):
        """Display category with color coding."""
        if obj.category:
            return format_html(
                '<span style="color: {}; font-weight: bold;">● {}</span>',
                obj.category.color_code,
                obj.category.name
            )
        return '-'
    colored_category.short_description = 'Category'
    
    def colored_status(self, obj):
        """Display status with color coding."""
        colors = {
            'active': '#28a745',
            'inactive': '#6c757d',
            'under_review': '#ffc107',
            'approved': '#17a2b8',
            'suspended': '#dc3545',
            'terminated': '#343a40'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    colored_status.short_description = 'Status'
    
    def colored_risk_level(self, obj):
        """Display risk level with color coding."""
        colors = {
            'low': '#28a745',
            'medium': '#ffc107',
            'high': '#fd7e14',
            'critical': '#dc3545'
        }
        color = colors.get(obj.risk_level, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_risk_level_display().upper()
        )
    colored_risk_level.short_description = 'Risk Level'
    
    def assigned_to_link(self, obj):
        """Display assigned user as clickable link."""
        if obj.assigned_to:
            return format_html(
                '<a href="{}">{}</a>',
                reverse('admin:auth_user_change', args=[obj.assigned_to.pk]),
                obj.assigned_to.get_full_name() or obj.assigned_to.username
            )
        return '-'
    assigned_to_link.short_description = 'Assigned To'
    
    def contract_status(self, obj):
        """Display contract expiration status."""
        if not obj.contract_end_date:
            return format_html('<span style="color: #6c757d;">No Contract</span>')
        
        days = obj.days_until_contract_expiry
        if days is None:
            return '-'
        elif days < 0:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">Expired {} days ago</span>',
                abs(days)
            )
        elif days <= obj.renewal_notice_days:
            return format_html(
                '<span style="color: #fd7e14; font-weight: bold;">Expires in {} days</span>',
                days
            )
        else:
            return format_html('<span style="color: #28a745;">Active ({} days)</span>', days)
    contract_status.short_description = 'Contract Status'
    
    def performance_indicator(self, obj):
        """Display performance score with visual indicator."""
        if obj.performance_score is None:
            return '-'
        
        score = float(obj.performance_score)
        if score >= 80:
            color = '#28a745'
            icon = '●'
        elif score >= 60:
            color = '#ffc107'
            icon = '●'
        else:
            color = '#dc3545'
            icon = '●'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {:.1f}%</span>',
            color, icon, score
        )
    performance_indicator.short_description = 'Performance'
    
    def contact_count(self, obj):
        """Display contact count with link."""
        count = obj.contacts.filter(is_active=True).count()
        url = reverse('admin:vendors_vendorcontact_changelist') + f'?vendor__id__exact={obj.id}'
        return format_html('<a href="{}">{}</a>', url, count)
    contact_count.short_description = 'Contacts'
    
    def service_count(self, obj):
        """Display service count with link."""
        count = obj.services.filter(is_active=True).count()
        url = reverse('admin:vendors_vendorservice_changelist') + f'?vendor__id__exact={obj.id}'
        return format_html('<a href="{}">{}</a>', url, count)
    service_count.short_description = 'Services'
    
    # Bulk Actions
    def mark_active(self, request, queryset):
        """Mark selected vendors as active."""
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} vendor(s) marked as active.')
    mark_active.short_description = "Mark selected vendors as active"
    
    def mark_inactive(self, request, queryset):
        """Mark selected vendors as inactive."""
        updated = queryset.update(status='inactive')
        self.message_user(request, f'{updated} vendor(s) marked as inactive.')
    mark_inactive.short_description = "Mark selected vendors as inactive"
    
    def mark_approved(self, request, queryset):
        """Mark selected vendors as approved."""
        updated = queryset.update(status='approved')
        self.message_user(request, f'{updated} vendor(s) marked as approved.')
    mark_approved.short_description = "Mark selected vendors as approved"


@admin.register(VendorContact)
class VendorContactAdmin(admin.ModelAdmin):
    """Admin interface for vendor contacts."""
    
    list_display = [
        'full_name', 'vendor_link', 'colored_contact_type', 
        'email', 'phone', 'is_primary_indicator', 'is_active', 'created_at'
    ]
    list_filter = ['contact_type', 'is_primary', 'is_active', 'preferred_communication', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'vendor__name']
    readonly_fields = ['created_at', 'updated_at']
    
    def vendor_link(self, obj):
        """Display vendor as clickable link."""
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:vendors_vendor_change', args=[obj.vendor.pk]),
            obj.vendor.name
        )
    vendor_link.short_description = 'Vendor'
    
    def colored_contact_type(self, obj):
        """Display contact type with color coding."""
        colors = {
            'primary': '#17a2b8',
            'billing': '#28a745',
            'technical': '#fd7e14',
            'legal': '#6f42c1',
            'security': '#dc3545',
            'account_manager': '#20c997',
            'executive': '#343a40',
            'emergency': '#e83e8c'
        }
        color = colors.get(obj.contact_type, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_contact_type_display()
        )
    colored_contact_type.short_description = 'Type'
    
    def is_primary_indicator(self, obj):
        """Display primary contact indicator."""
        if obj.is_primary:
            return format_html('<span style="color: #28a745; font-weight: bold;">★ Primary</span>')
        return '-'
    is_primary_indicator.short_description = 'Primary'


@admin.register(VendorService)
class VendorServiceAdmin(admin.ModelAdmin):
    """Admin interface for vendor services."""
    
    list_display = [
        'name', 'vendor_link', 'colored_category', 'data_classification_indicator',
        'cost_display', 'billing_frequency', 'risk_assessment_status', 'is_active', 'created_at'
    ]
    list_filter = [
        'category', 'data_classification', 'billing_frequency',
        'risk_assessment_required', 'risk_assessment_completed', 'is_active', 'created_at'
    ]
    search_fields = ['name', 'description', 'service_code', 'vendor__name']
    readonly_fields = ['created_at', 'updated_at']
    
    def vendor_link(self, obj):
        """Display vendor as clickable link."""
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:vendors_vendor_change', args=[obj.vendor.pk]),
            obj.vendor.name
        )
    vendor_link.short_description = 'Vendor'
    
    def colored_category(self, obj):
        """Display service category with color coding."""
        return format_html(
            '<span style="font-weight: bold;">{}</span>',
            obj.get_category_display()
        )
    colored_category.short_description = 'Category'
    
    def data_classification_indicator(self, obj):
        """Display data classification with color coding."""
        colors = {
            'public': '#28a745',
            'internal': '#ffc107',
            'confidential': '#fd7e14',
            'restricted': '#dc3545'
        }
        color = colors.get(obj.data_classification, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_data_classification_display().upper()
        )
    data_classification_indicator.short_description = 'Data Classification'
    
    def cost_display(self, obj):
        """Display cost information."""
        if obj.cost_per_unit:
            return f'${obj.cost_per_unit:,.2f}'
        return '-'
    cost_display.short_description = 'Cost/Unit'
    
    def risk_assessment_status(self, obj):
        """Display risk assessment status."""
        if not obj.risk_assessment_required:
            return format_html('<span style="color: #6c757d;">Not Required</span>')
        elif obj.risk_assessment_completed:
            return format_html('<span style="color: #28a745; font-weight: bold;">✓ Complete</span>')
        else:
            return format_html('<span style="color: #dc3545; font-weight: bold;">✗ Pending</span>')
    risk_assessment_status.short_description = 'Risk Assessment'


@admin.register(VendorNote)
class VendorNoteAdmin(admin.ModelAdmin):
    """Admin interface for vendor notes."""
    
    list_display = [
        'title', 'vendor_link', 'colored_note_type', 
        'created_by_name', 'internal_indicator', 'created_at'
    ]
    list_filter = ['note_type', 'is_internal', 'created_by', 'created_at']
    search_fields = ['title', 'content', 'vendor__name']
    readonly_fields = ['created_at', 'created_by']
    
    def vendor_link(self, obj):
        """Display vendor as clickable link."""
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:vendors_vendor_change', args=[obj.vendor.pk]),
            obj.vendor.name
        )
    vendor_link.short_description = 'Vendor'
    
    def colored_note_type(self, obj):
        """Display note type with color coding."""
        colors = {
            'general': '#6c757d',
            'meeting': '#17a2b8',
            'issue': '#dc3545',
            'performance': '#28a745',
            'contract': '#ffc107',
            'security': '#fd7e14',
            'compliance': '#6f42c1',
            'renewal': '#20c997'
        }
        color = colors.get(obj.note_type, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_note_type_display()
        )
    colored_note_type.short_description = 'Type'
    
    def created_by_name(self, obj):
        """Display creator name."""
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return '-'
    created_by_name.short_description = 'Created By'
    
    def internal_indicator(self, obj):
        """Display internal note indicator."""
        if obj.is_internal:
            return format_html('<span style="color: #fd7e14; font-weight: bold;">🔒 Internal</span>')
        return '-'
    internal_indicator.short_description = 'Internal'


@admin.register(VendorTask)
class VendorTaskAdmin(admin.ModelAdmin):
    """Professional admin interface for vendor task management."""
    
    list_display = [
        'task_id', 'colored_title', 'vendor_link', 'colored_task_type',
        'colored_status', 'colored_priority', 'due_date_display',
        'assigned_to_name', 'days_until_due_display', 'auto_generated_indicator'
    ]
    list_filter = [
        'task_type', 'status', 'priority', 'auto_generated', 'is_recurring',
        'vendor__status', 'vendor__risk_level', 'due_date', 'created_at'
    ]
    search_fields = [
        'task_id', 'title', 'description', 'vendor__name', 
        'vendor__vendor_id', 'related_contract_number'
    ]
    list_editable = ['status', 'priority', 'assigned_to']
    readonly_fields = [
        'task_id', 'auto_generated', 'generation_source', 'completed_date',
        'days_until_due', 'is_overdue', 'should_send_reminder', 'next_reminder_date',
        'created_at', 'updated_at'
    ]
    date_hierarchy = 'due_date'
    list_per_page = 25
    ordering = ['due_date', '-priority']
    
    fieldsets = (
        ('Task Information', {
            'fields': (
                'task_id', 'vendor', 'task_type', 'title', 'description'
            )
        }),
        ('Scheduling', {
            'fields': (
                'due_date', 'start_date', 'completed_date', 'status', 'priority'
            )
        }),
        ('Assignment', {
            'fields': (
                'assigned_to', 'created_by'
            )
        }),
        ('Reminders', {
            'fields': (
                'reminder_days', 'last_reminder_sent', 'reminder_recipients'
            ),
            'classes': ('collapse',)
        }),
        ('Integration', {
            'fields': (
                'related_contract_number', 'service_reference'
            ),
            'classes': ('collapse',)
        }),
        ('Completion & Results', {
            'fields': (
                'completion_notes', 'attachments'
            ),
            'classes': ('collapse',)
        }),
        ('Recurrence', {
            'fields': (
                'is_recurring', 'recurrence_pattern', 'parent_task'
            ),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': (
                'auto_generated', 'generation_source', 'days_until_due', 
                'is_overdue', 'should_send_reminder', 'next_reminder_date',
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    actions = [
        'mark_as_completed', 'mark_as_in_progress', 'mark_as_pending',
        'assign_to_me', 'send_reminders', 'mark_as_high_priority'
    ]
    
    def get_queryset(self, request):
        """Optimize queryset with related data."""
        return super().get_queryset(request).select_related(
            'vendor', 'assigned_to', 'created_by', 'service_reference', 'parent_task'
        )
    
    def colored_title(self, obj):
        """Display task title with color coding based on urgency."""
        if obj.is_overdue:
            color = '#dc3545'  # Red for overdue
            icon = '🚨'
        elif obj.days_until_due is not None and obj.days_until_due <= 1:
            color = '#fd7e14'  # Orange for due soon
            icon = '⚠️'
        elif obj.status == 'completed':
            color = '#28a745'  # Green for completed
            icon = '✅'
        else:
            color = '#333'
            icon = '📋'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.title[:50] + ('...' if len(obj.title) > 50 else '')
        )
    colored_title.short_description = 'Task'
    colored_title.admin_order_field = 'title'
    
    def vendor_link(self, obj):
        """Display vendor with link to vendor admin."""
        url = reverse('admin:vendors_vendor_change', args=[obj.vendor.pk])
        return format_html(
            '<a href="{}" style="text-decoration: none;">{}</a>',
            url, obj.vendor.name
        )
    vendor_link.short_description = 'Vendor'
    vendor_link.admin_order_field = 'vendor__name'
    
    def colored_task_type(self, obj):
        """Display task type with color coding."""
        colors = {
            'contract_renewal': '#dc3545',
            'contract_renegotiation': '#fd7e14',
            'security_review': '#6f42c1',
            'compliance_assessment': '#0d6efd',
            'performance_review': '#198754',
            'risk_assessment': '#fd7e14',
            'audit': '#6610f2',
            'certification_renewal': '#20c997',
            'data_processing_agreement': '#0dcaf0',
            'onboarding': '#28a745',
            'offboarding': '#dc3545',
            'custom': '#6c757d'
        }
        color = colors.get(obj.task_type, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_task_type_display()
        )
    colored_task_type.short_description = 'Type'
    colored_task_type.admin_order_field = 'task_type'
    
    def colored_status(self, obj):
        """Display status with color coding."""
        colors = {
            'pending': '#6c757d',
            'in_progress': '#0d6efd',
            'completed': '#28a745',
            'overdue': '#dc3545',
            'cancelled': '#6c757d',
            'on_hold': '#fd7e14'
        }
        icons = {
            'pending': '⏳',
            'in_progress': '🔄',
            'completed': '✅',
            'overdue': '🚨',
            'cancelled': '❌',
            'on_hold': '⏸️'
        }
        color = colors.get(obj.status, '#6c757d')
        icon = icons.get(obj.status, '📋')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    colored_status.short_description = 'Status'
    colored_status.admin_order_field = 'status'
    
    def colored_priority(self, obj):
        """Display priority with color coding."""
        colors = {
            'low': '#28a745',
            'medium': '#fd7e14',
            'high': '#dc3545',
            'urgent': '#6f42c1',
            'critical': '#dc3545'
        }
        icons = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🟠',
            'urgent': '🔴',
            'critical': '🚨'
        }
        color = colors.get(obj.priority, '#6c757d')
        icon = icons.get(obj.priority, '📋')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_priority_display()
        )
    colored_priority.short_description = 'Priority'
    colored_priority.admin_order_field = 'priority'
    
    def due_date_display(self, obj):
        """Display due date with visual indicators."""
        if not obj.due_date:
            return '-'
        
        today = timezone.now().date()
        if obj.due_date < today:
            # Overdue
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">🚨 {} (OVERDUE)</span>',
                obj.due_date.strftime('%b %d, %Y')
            )
        elif obj.due_date == today:
            # Due today
            return format_html(
                '<span style="color: #fd7e14; font-weight: bold;">⚠️ {} (TODAY)</span>',
                obj.due_date.strftime('%b %d, %Y')
            )
        elif obj.due_date <= today + timezone.timedelta(days=7):
            # Due this week
            return format_html(
                '<span style="color: #fd7e14; font-weight: bold;">⏰ {}</span>',
                obj.due_date.strftime('%b %d, %Y')
            )
        else:
            # Normal
            return obj.due_date.strftime('%b %d, %Y')
    
    due_date_display.short_description = 'Due Date'
    due_date_display.admin_order_field = 'due_date'
    
    def assigned_to_name(self, obj):
        """Display assigned user name."""
        if obj.assigned_to:
            return obj.assigned_to.get_full_name() or obj.assigned_to.username
        return format_html('<span style="color: #fd7e14;">Unassigned</span>')
    assigned_to_name.short_description = 'Assigned To'
    assigned_to_name.admin_order_field = 'assigned_to__username'
    
    def days_until_due_display(self, obj):
        """Display days until due with color coding."""
        days = obj.days_until_due
        if days is None:
            return '-'
        
        if days < 0:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">{} days overdue</span>',
                abs(days)
            )
        elif days == 0:
            return format_html(
                '<span style="color: #fd7e14; font-weight: bold;">Due today</span>'
            )
        elif days <= 7:
            return format_html(
                '<span style="color: #fd7e14;">{} days</span>',
                days
            )
        else:
            return f"{days} days"
    days_until_due_display.short_description = 'Days Until Due'
    
    def auto_generated_indicator(self, obj):
        """Display auto-generated indicator."""
        if obj.auto_generated:
            return format_html(
                '<span style="color: #0d6efd;" title="Auto-generated: {}">🤖 Auto</span>',
                obj.generation_source or 'Unknown'
            )
        return format_html('<span style="color: #6c757d;">👤 Manual</span>')
    auto_generated_indicator.short_description = 'Source'
    
    # Admin Actions
    def mark_as_completed(self, request, queryset):
        """Mark selected tasks as completed."""
        count = 0
        for task in queryset:
            if task.status != 'completed':
                task.status = 'completed'
                task.save()
                count += 1
        
        self.message_user(request, f'Successfully marked {count} tasks as completed.')
    mark_as_completed.short_description = "Mark selected tasks as completed"
    
    def mark_as_in_progress(self, request, queryset):
        """Mark selected tasks as in progress."""
        count = queryset.exclude(status='in_progress').update(status='in_progress')
        self.message_user(request, f'Successfully marked {count} tasks as in progress.')
    mark_as_in_progress.short_description = "Mark selected tasks as in progress"
    
    def mark_as_pending(self, request, queryset):
        """Mark selected tasks as pending."""
        count = queryset.exclude(status='pending').update(status='pending')
        self.message_user(request, f'Successfully marked {count} tasks as pending.')
    mark_as_pending.short_description = "Mark selected tasks as pending"
    
    def assign_to_me(self, request, queryset):
        """Assign selected tasks to current user."""
        count = queryset.update(assigned_to=request.user)
        self.message_user(request, f'Successfully assigned {count} tasks to you.')
    assign_to_me.short_description = "Assign selected tasks to me"
    
    def send_reminders(self, request, queryset):
        """Send reminders for selected tasks."""
        from .task_notifications import get_notification_service
        
        notification_service = get_notification_service()
        tasks = list(queryset.filter(status__in=['pending', 'in_progress']))
        results = notification_service.send_batch_reminders(tasks)
        
        self.message_user(
            request, 
            f'Sent {results.get("sent", 0)} reminders, {results.get("failed", 0)} failed.'
        )
    send_reminders.short_description = "Send reminders for selected tasks"
    
    def mark_as_high_priority(self, request, queryset):
        """Mark selected tasks as high priority."""
        count = queryset.update(priority='high')
        self.message_user(request, f'Successfully marked {count} tasks as high priority.')
    mark_as_high_priority.short_description = "Mark selected tasks as high priority"