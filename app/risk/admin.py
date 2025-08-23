from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count
from .models import (
    Risk, RiskCategory, RiskMatrix, RiskNote,
    RiskAction, RiskActionNote, RiskActionEvidence,
    RiskActionReminderConfiguration
)


@admin.register(RiskCategory)
class RiskCategoryAdmin(admin.ModelAdmin):
    """Admin configuration for Risk Categories."""
    
    list_display = ['name', 'risk_count', 'color_display', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    ordering = ['name']
    
    def get_queryset(self, request):
        """Optimize queryset with risk counts."""
        return super().get_queryset(request).annotate(
            risk_count=Count('risks')
        )
    
    def risk_count(self, obj):
        """Display risk count for this category."""
        return obj.risk_count
    risk_count.short_description = 'Risks'
    risk_count.admin_order_field = 'risk_count'
    
    def color_display(self, obj):
        """Display color with visual indicator."""
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc; display: inline-block; margin-right: 10px;"></div>{}',
            obj.color,
            obj.color
        )
    color_display.short_description = 'Color'


@admin.register(RiskMatrix)
class RiskMatrixAdmin(admin.ModelAdmin):
    """Admin configuration for Risk Matrices."""
    
    list_display = [
        'name', 'dimensions_display', 'is_default', 'risk_count', 
        'created_by_name', 'created_at'
    ]
    list_filter = ['is_default', 'impact_levels', 'likelihood_levels', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'description', 'is_default']
        }),
        ('Matrix Configuration', {
            'fields': ['impact_levels', 'likelihood_levels', 'matrix_config']
        }),
        ('Metadata', {
            'fields': ['created_at', 'updated_at', 'created_by'],
            'classes': ['collapse']
        }),
    ]
    
    def get_queryset(self, request):
        """Optimize queryset with related data."""
        return super().get_queryset(request).select_related(
            'created_by'
        ).annotate(
            risk_count=Count('risk')
        )
    
    def dimensions_display(self, obj):
        """Display matrix dimensions."""
        return f"{obj.impact_levels}×{obj.likelihood_levels}"
    dimensions_display.short_description = 'Dimensions'
    
    def risk_count(self, obj):
        """Display count of risks using this matrix."""
        return obj.risk_count
    risk_count.short_description = 'Risks Using Matrix'
    risk_count.admin_order_field = 'risk_count'
    
    def created_by_name(self, obj):
        """Display creator name."""
        return obj.created_by.get_full_name() if obj.created_by else 'System'
    created_by_name.short_description = 'Created By'
    created_by_name.admin_order_field = 'created_by__first_name'
    
    def save_model(self, request, obj, form, change):
        """Set creator on new objects."""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class RiskNoteInline(admin.TabularInline):
    """Inline admin for Risk Notes."""
    
    model = RiskNote
    fields = ['note_type', 'note', 'created_by', 'created_at']
    readonly_fields = ['created_at']
    extra = 0
    can_delete = True
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('created_by')


@admin.register(Risk)
class RiskAdmin(admin.ModelAdmin):
    """Admin configuration for Risks with comprehensive management features."""
    
    list_display = [
        'risk_id', 'title', 'risk_level_colored', 'risk_score_display',
        'status_colored', 'category', 'risk_owner_display', 
        'next_review_display', 'created_at'
    ]
    
    list_filter = [
        'risk_level', 'status', 'treatment_strategy', 'category',
        ('risk_owner', admin.RelatedOnlyFieldListFilter),
        'identified_date', 'last_assessed_date', 'created_at',
        ('next_review_date', admin.DateFieldListFilter),
    ]
    
    search_fields = [
        'risk_id', 'title', 'description', 
        'potential_impact_description', 'current_controls'
    ]
    
    readonly_fields = [
        'risk_id', 'risk_level', 'risk_score_display', 'last_assessed_date',
        'closed_date', 'created_at', 'updated_at', 'days_until_review_display',
        'is_overdue_for_review'
    ]
    
    # autocomplete_fields = ['risk_owner', 'created_by']  # Disabled until User admin is registered
    
    fieldsets = [
        ('Risk Identification', {
            'fields': [
                'risk_id', 'title', 'description', 'category',
                'identified_date'
            ]
        }),
        ('Risk Assessment', {
            'fields': [
                'impact', 'likelihood', 'risk_level', 'risk_score_display',
                'risk_matrix', 'last_assessed_date'
            ]
        }),
        ('Risk Management', {
            'fields': [
                'status', 'treatment_strategy', 'treatment_description',
                'risk_owner', 'next_review_date', 'days_until_review_display',
                'is_overdue_for_review'
            ]
        }),
        ('Additional Information', {
            'fields': [
                'potential_impact_description', 'current_controls'
            ],
            'classes': ['collapse']
        }),
        ('Dates', {
            'fields': ['closed_date', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
        ('Metadata', {
            'fields': ['created_by'],
            'classes': ['collapse']
        }),
    ]
    
    inlines = [RiskNoteInline]
    
    actions = [
        'mark_as_assessed',
        'mark_as_treatment_planned',
        'mark_as_mitigated',
        'set_next_review_date',
        'bulk_assign_owner',
    ]
    
    def get_queryset(self, request):
        """Optimize queryset with related data."""
        return super().get_queryset(request).select_related(
            'category', 'risk_owner', 'risk_matrix', 'created_by'
        ).prefetch_related('notes')
    
    def risk_level_colored(self, obj):
        """Display risk level with color coding."""
        colors = {
            'low': '#10B981',      # Green
            'medium': '#F59E0B',   # Yellow
            'high': '#EF4444',     # Red
            'critical': '#DC2626', # Dark Red
        }
        color = colors.get(obj.risk_level, '#6B7280')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_risk_level_display()
        )
    risk_level_colored.short_description = 'Risk Level'
    risk_level_colored.admin_order_field = 'risk_level'
    
    def status_colored(self, obj):
        """Display status with color coding."""
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
        color = colors.get(obj.status, '#6B7280')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'
    status_colored.admin_order_field = 'status'
    
    def risk_score_display(self, obj):
        """Display calculated risk score."""
        return f"{obj.risk_score} ({obj.impact}×{obj.likelihood})"
    risk_score_display.short_description = 'Risk Score'
    
    def risk_owner_display(self, obj):
        """Display risk owner with link."""
        if obj.risk_owner:
            url = reverse('admin:core_user_change', args=[obj.risk_owner.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.risk_owner.get_full_name() or obj.risk_owner.username
            )
        return 'Unassigned'
    risk_owner_display.short_description = 'Risk Owner'
    risk_owner_display.admin_order_field = 'risk_owner__first_name'
    
    def next_review_display(self, obj):
        """Display next review date with overdue indicator."""
        if not obj.next_review_date:
            return 'Not scheduled'
        
        if obj.is_overdue_for_review:
            return format_html(
                '<span style="color: #DC2626; font-weight: bold;">{} (Overdue)</span>',
                obj.next_review_date
            )
        elif obj.days_until_review is not None and obj.days_until_review <= 7:
            return format_html(
                '<span style="color: #F59E0B;">{} ({} days)</span>',
                obj.next_review_date,
                obj.days_until_review
            )
        else:
            return obj.next_review_date
    next_review_display.short_description = 'Next Review'
    next_review_display.admin_order_field = 'next_review_date'
    
    def days_until_review_display(self, obj):
        """Display days until review with status."""
        if obj.days_until_review is None:
            return 'Not scheduled'
        elif obj.days_until_review < 0:
            return format_html(
                '<span style="color: #DC2626; font-weight: bold;">{} days overdue</span>',
                abs(obj.days_until_review)
            )
        else:
            return f"{obj.days_until_review} days"
    days_until_review_display.short_description = 'Days Until Review'
    
    def save_model(self, request, obj, form, change):
        """Set creator on new objects."""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    # Admin Actions
    def mark_as_assessed(self, request, queryset):
        """Mark selected risks as assessed."""
        count = queryset.update(status='assessed')
        self.message_user(request, f'Successfully marked {count} risks as assessed.')
    mark_as_assessed.short_description = 'Mark selected risks as assessed'
    
    def mark_as_treatment_planned(self, request, queryset):
        """Mark selected risks as treatment planned."""
        count = queryset.update(status='treatment_planned')
        self.message_user(request, f'Successfully marked {count} risks as treatment planned.')
    mark_as_treatment_planned.short_description = 'Mark selected risks as treatment planned'
    
    def mark_as_mitigated(self, request, queryset):
        """Mark selected risks as mitigated."""
        count = queryset.update(status='mitigated')
        self.message_user(request, f'Successfully marked {count} risks as mitigated.')
    mark_as_mitigated.short_description = 'Mark selected risks as mitigated'
    
    def set_next_review_date(self, request, queryset):
        """Set next review date for selected risks."""
        # This would typically open a form to set the date
        # For simplicity, setting to 90 days from now
        review_date = timezone.now().date() + timezone.timedelta(days=90)
        count = queryset.update(next_review_date=review_date)
        self.message_user(request, f'Set next review date for {count} risks to {review_date}.')
    set_next_review_date.short_description = 'Set next review date (90 days from now)'


@admin.register(RiskNote)
class RiskNoteAdmin(admin.ModelAdmin):
    """Admin configuration for Risk Notes."""
    
    list_display = [
        'risk_display', 'note_type', 'note_preview', 
        'created_by_display', 'created_at'
    ]
    
    list_filter = [
        'note_type', 'created_at',
        ('created_by', admin.RelatedOnlyFieldListFilter),
    ]
    
    search_fields = ['risk__risk_id', 'risk__title', 'note']
    
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related(
            'risk', 'created_by'
        )
    
    def risk_display(self, obj):
        """Display linked risk."""
        url = reverse('admin:risk_risk_change', args=[obj.risk.pk])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.risk.risk_id
        )
    risk_display.short_description = 'Risk'
    risk_display.admin_order_field = 'risk__risk_id'
    
    def note_preview(self, obj):
        """Display note preview."""
        return obj.note[:100] + '...' if len(obj.note) > 100 else obj.note
    note_preview.short_description = 'Note Preview'
    
    def created_by_display(self, obj):
        """Display creator name."""
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return 'System'
    created_by_display.short_description = 'Created By'
    created_by_display.admin_order_field = 'created_by__first_name'


# Risk Action Admin Classes

class RiskActionNoteInline(admin.TabularInline):
    """Inline admin for Risk Action Notes."""
    
    model = RiskActionNote
    fields = ['note_type', 'note', 'progress_percentage', 'created_by', 'created_at']
    readonly_fields = ['created_at']
    extra = 0
    can_delete = True
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('created_by')


class RiskActionEvidenceInline(admin.TabularInline):
    """Inline admin for Risk Action Evidence."""
    
    model = RiskActionEvidence
    fields = ['title', 'evidence_type', 'file', 'external_link', 'is_validated', 'uploaded_by', 'evidence_date']
    readonly_fields = ['uploaded_by', 'evidence_date', 'is_validated', 'validated_by', 'validated_at']
    extra = 0
    can_delete = True
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('uploaded_by', 'validated_by')


@admin.register(RiskAction)
class RiskActionAdmin(admin.ModelAdmin):
    """Admin configuration for Risk Actions with comprehensive management features."""
    
    list_display = [
        'action_id', 'title', 'risk_display', 'priority_colored', 
        'status_colored', 'progress_bar', 'assigned_to_display',
        'due_date_display', 'created_at'
    ]
    
    list_filter = [
        'status', 'priority', 'action_type',
        ('assigned_to', admin.RelatedOnlyFieldListFilter),
        ('risk', admin.RelatedOnlyFieldListFilter),
        'due_date', 'start_date', 'completed_date', 'created_at',
    ]
    
    search_fields = [
        'action_id', 'title', 'description', 'risk__risk_id', 'risk__title'
    ]
    
    readonly_fields = [
        'action_id', 'days_until_due_display', 'is_overdue', 'is_due_soon',
        'completed_date', 'created_at', 'updated_at'
    ]
    
    # autocomplete_fields = ['assigned_to', 'created_by']  # Disabled until User admin is registered
    
    fieldsets = [
        ('Action Information', {
            'fields': [
                'action_id', 'title', 'description', 'action_type',
                'risk'
            ]
        }),
        ('Assignment & Priority', {
            'fields': [
                'assigned_to', 'priority', 'status', 'progress_percentage'
            ]
        }),
        ('Scheduling', {
            'fields': [
                'start_date', 'due_date', 'completed_date',
                'days_until_due_display', 'is_overdue', 'is_due_soon'
            ]
        }),
        ('Cost & Effort', {
            'fields': [
                'estimated_cost', 'actual_cost', 'estimated_effort_hours'
            ],
            'classes': ['collapse']
        }),
        ('Requirements', {
            'fields': [
                'success_criteria', 'dependencies'
            ],
            'classes': ['collapse']
        }),
        ('Metadata', {
            'fields': ['created_at', 'updated_at', 'created_by'],
            'classes': ['collapse']
        }),
    ]
    
    inlines = [RiskActionNoteInline, RiskActionEvidenceInline]
    
    actions = [
        'mark_as_in_progress',
        'mark_as_completed',
        'mark_as_deferred',
        'set_high_priority',
        'bulk_assign_user',
        'send_reminder_notifications',
    ]
    
    def get_queryset(self, request):
        """Optimize queryset with related data."""
        return super().get_queryset(request).select_related(
            'risk', 'assigned_to', 'created_by'
        ).prefetch_related('notes', 'evidence')
    
    def risk_display(self, obj):
        """Display linked risk with level indicator."""
        if obj.risk:
            url = reverse('admin:risk_risk_change', args=[obj.risk.pk])
            color = obj.risk.get_risk_level_color()
            return format_html(
                '<a href="{}" style="color: {};">{}</a>',
                url,
                color,
                obj.risk.risk_id
            )
        return 'No Risk'
    risk_display.short_description = 'Risk'
    risk_display.admin_order_field = 'risk__risk_id'
    
    def priority_colored(self, obj):
        """Display priority with color coding."""
        colors = {
            'low': '#10B981',      # Green
            'medium': '#F59E0B',   # Yellow
            'high': '#EF4444',     # Red
            'critical': '#DC2626', # Dark Red
        }
        color = colors.get(obj.priority, '#6B7280')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_colored.short_description = 'Priority'
    priority_colored.admin_order_field = 'priority'
    
    def status_colored(self, obj):
        """Display status with color coding."""
        colors = {
            'pending': '#6B7280',           # Gray
            'in_progress': '#3B82F6',       # Blue
            'completed': '#10B981',         # Green
            'cancelled': '#EF4444',         # Red
            'deferred': '#F59E0B',          # Yellow
        }
        color = colors.get(obj.status, '#6B7280')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'
    status_colored.admin_order_field = 'status'
    
    def progress_bar(self, obj):
        """Display progress as a visual bar."""
        progress = obj.progress_percentage
        if progress == 0:
            color = '#e5e7eb'  # Gray
        elif progress < 25:
            color = '#ef4444'  # Red
        elif progress < 50:
            color = '#f59e0b'  # Yellow
        elif progress < 75:
            color = '#3b82f6'  # Blue
        else:
            color = '#10b981'  # Green
        
        return format_html(
            '<div style="width: 100px; background-color: #e5e7eb; border-radius: 3px; height: 12px;">'
            '<div style="width: {}%; background-color: {}; height: 100%; border-radius: 3px; text-align: center; line-height: 12px; font-size: 10px; color: white;">'
            '{}'
            '</div>'
            '</div>',
            progress,
            color,
            f'{progress}%' if progress > 20 else ''
        )
    progress_bar.short_description = 'Progress'
    progress_bar.admin_order_field = 'progress_percentage'
    
    def assigned_to_display(self, obj):
        """Display assigned user with link."""
        if obj.assigned_to:
            url = reverse('admin:core_user_change', args=[obj.assigned_to.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.assigned_to.get_full_name() or obj.assigned_to.username
            )
        return 'Unassigned'
    assigned_to_display.short_description = 'Assigned To'
    assigned_to_display.admin_order_field = 'assigned_to__first_name'
    
    def due_date_display(self, obj):
        """Display due date with overdue indicator."""
        if not obj.due_date:
            return 'Not set'
        
        if obj.is_overdue:
            return format_html(
                '<span style="color: #DC2626; font-weight: bold;">{} (Overdue)</span>',
                obj.due_date
            )
        elif obj.is_due_soon:
            return format_html(
                '<span style="color: #F59E0B;">{} (Due Soon)</span>',
                obj.due_date
            )
        else:
            return obj.due_date
    due_date_display.short_description = 'Due Date'
    due_date_display.admin_order_field = 'due_date'
    
    def days_until_due_display(self, obj):
        """Display days until due with status."""
        days = obj.days_until_due
        if days < 0:
            return format_html(
                '<span style="color: #DC2626; font-weight: bold;">{} days overdue</span>',
                abs(days)
            )
        elif days == 0:
            return format_html(
                '<span style="color: #F59E0B; font-weight: bold;">Due today</span>'
            )
        else:
            return f"{days} days remaining"
    days_until_due_display.short_description = 'Days Until Due'
    
    def save_model(self, request, obj, form, change):
        """Set creator on new objects and send notifications."""
        if not change:
            obj.created_by = request.user
            
        # Check if assigned_to changed for notifications
        old_assigned_to = None
        if change and obj.pk:
            try:
                old_obj = RiskAction.objects.get(pk=obj.pk)
                old_assigned_to = old_obj.assigned_to
            except RiskAction.DoesNotExist:
                pass
        
        super().save_model(request, obj, form, change)
        
        # Send assignment notification if assigned user changed
        if obj.assigned_to and obj.assigned_to != old_assigned_to:
            from .notifications import RiskActionReminderService
            RiskActionReminderService.send_assignment_notification(
                obj, obj.assigned_to, request.user
            )
    
    # Admin Actions
    def mark_as_in_progress(self, request, queryset):
        """Mark selected actions as in progress."""
        count = queryset.update(status='in_progress')
        self.message_user(request, f'Successfully marked {count} actions as in progress.')
    mark_as_in_progress.short_description = 'Mark selected actions as in progress'
    
    def mark_as_completed(self, request, queryset):
        """Mark selected actions as completed."""
        count = queryset.update(status='completed', progress_percentage=100)
        self.message_user(request, f'Successfully marked {count} actions as completed.')
    mark_as_completed.short_description = 'Mark selected actions as completed'
    
    def mark_as_deferred(self, request, queryset):
        """Mark selected actions as deferred."""
        count = queryset.update(status='deferred')
        self.message_user(request, f'Successfully marked {count} actions as deferred.')
    mark_as_deferred.short_description = 'Mark selected actions as deferred'
    
    def set_high_priority(self, request, queryset):
        """Set selected actions to high priority."""
        count = queryset.update(priority='high')
        self.message_user(request, f'Set {count} actions to high priority.')
    set_high_priority.short_description = 'Set selected actions to high priority'
    
    def send_reminder_notifications(self, request, queryset):
        """Send immediate reminder notifications for selected actions."""
        from .tasks import send_immediate_risk_action_reminder
        
        sent_count = 0
        for action in queryset.filter(assigned_to__isnull=False):
            send_immediate_risk_action_reminder.delay(
                action.id, action.assigned_to.id, 'advance_warning'
            )
            sent_count += 1
        
        self.message_user(
            request, 
            f'Queued {sent_count} reminder notifications for sending.'
        )
    send_reminder_notifications.short_description = 'Send reminder notifications'


@admin.register(RiskActionNote)
class RiskActionNoteAdmin(admin.ModelAdmin):
    """Admin configuration for Risk Action Notes."""
    
    list_display = [
        'action_display', 'note_type', 'note_preview', 'progress_display',
        'created_by_display', 'created_at'
    ]
    
    list_filter = [
        'note_type', 'created_at',
        ('created_by', admin.RelatedOnlyFieldListFilter),
        ('action__status', admin.ChoicesFieldListFilter),
    ]
    
    search_fields = ['action__action_id', 'action__title', 'note']
    
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related(
            'action', 'action__risk', 'created_by'
        )
    
    def action_display(self, obj):
        """Display linked action."""
        url = reverse('admin:risk_riskaction_change', args=[obj.action.pk])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.action.action_id
        )
    action_display.short_description = 'Action'
    action_display.admin_order_field = 'action__action_id'
    
    def note_preview(self, obj):
        """Display note preview."""
        return obj.note[:100] + '...' if len(obj.note) > 100 else obj.note
    note_preview.short_description = 'Note Preview'
    
    def progress_display(self, obj):
        """Display progress percentage if provided."""
        return f"{obj.progress_percentage}%" if obj.progress_percentage is not None else 'N/A'
    progress_display.short_description = 'Progress'
    
    def created_by_display(self, obj):
        """Display creator name."""
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return 'System'
    created_by_display.short_description = 'Created By'
    created_by_display.admin_order_field = 'created_by__first_name'


@admin.register(RiskActionEvidence)
class RiskActionEvidenceAdmin(admin.ModelAdmin):
    """Admin configuration for Risk Action Evidence."""
    
    list_display = [
        'title', 'action_display', 'evidence_type', 'validation_status',
        'uploaded_by_display', 'evidence_date'
    ]
    
    list_filter = [
        'evidence_type', 'is_validated', 'evidence_date',
        ('uploaded_by', admin.RelatedOnlyFieldListFilter),
        ('validated_by', admin.RelatedOnlyFieldListFilter),
    ]
    
    search_fields = ['title', 'description', 'action__action_id', 'action__title']
    
    readonly_fields = [
        'uploaded_by', 'created_at', 'validated_by', 'validated_at'
    ]
    
    fieldsets = [
        ('Evidence Information', {
            'fields': [
                'title', 'description', 'evidence_type', 'action'
            ]
        }),
        ('Files & Links', {
            'fields': [
                'file', 'external_link'
            ]
        }),
        ('Validation', {
            'fields': [
                'is_validated', 'validated_by', 'validated_at', 'validation_notes'
            ]
        }),
        ('Metadata', {
            'fields': [
                'evidence_date', 'uploaded_by', 'created_at'
            ],
            'classes': ['collapse']
        }),
    ]
    
    actions = [
        'mark_as_validated',
        'mark_as_unvalidated',
    ]
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related(
            'action', 'action__risk', 'uploaded_by', 'validated_by'
        )
    
    def action_display(self, obj):
        """Display linked action."""
        url = reverse('admin:risk_riskaction_change', args=[obj.action.pk])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.action.action_id
        )
    action_display.short_description = 'Action'
    action_display.admin_order_field = 'action__action_id'
    
    def validation_status(self, obj):
        """Display validation status with color."""
        if obj.is_validated:
            return format_html(
                '<span style="color: #10B981; font-weight: bold;">✓ Validated</span>'
            )
        else:
            return format_html(
                '<span style="color: #F59E0B;">⏳ Pending</span>'
            )
    validation_status.short_description = 'Validation'
    validation_status.admin_order_field = 'is_validated'
    
    def uploaded_by_display(self, obj):
        """Display uploader name."""
        if obj.uploaded_by:
            return obj.uploaded_by.get_full_name() or obj.uploaded_by.username
        return 'Unknown'
    uploaded_by_display.short_description = 'Uploaded By'
    uploaded_by_display.admin_order_field = 'uploaded_by__first_name'
    
    def mark_as_validated(self, request, queryset):
        """Mark selected evidence as validated."""
        count = queryset.update(
            is_validated=True,
            validated_by=request.user,
            validated_at=timezone.now()
        )
        self.message_user(request, f'Successfully validated {count} evidence items.')
    mark_as_validated.short_description = 'Mark as validated'
    
    def mark_as_unvalidated(self, request, queryset):
        """Mark selected evidence as unvalidated."""
        count = queryset.update(
            is_validated=False,
            validated_by=None,
            validated_at=None,
            validation_notes=''
        )
        self.message_user(request, f'Successfully marked {count} evidence items as unvalidated.')
    mark_as_unvalidated.short_description = 'Mark as unvalidated'


@admin.register(RiskActionReminderConfiguration)
class RiskActionReminderConfigurationAdmin(admin.ModelAdmin):
    """Admin configuration for Risk Action Reminder Configurations."""
    
    list_display = [
        'user_display', 'enable_reminders', 'advance_warning_days',
        'reminder_frequency', 'email_notifications', 'weekly_digest_enabled',
        'updated_at'
    ]
    
    list_filter = [
        'enable_reminders', 'email_notifications', 'reminder_frequency',
        'weekly_digest_enabled', 'overdue_reminders', 'silence_completed',
        'updated_at'
    ]
    
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = [
        ('User', {
            'fields': ['user']
        }),
        ('Reminder Settings', {
            'fields': [
                'enable_reminders', 'advance_warning_days', 'reminder_frequency',
                'custom_reminder_days'
            ]
        }),
        ('Notification Preferences', {
            'fields': [
                'email_notifications', 'overdue_reminders'
            ]
        }),
        ('Weekly Digest', {
            'fields': [
                'weekly_digest_enabled', 'weekly_digest_day'
            ]
        }),
        ('Auto-silence Options', {
            'fields': [
                'silence_completed', 'silence_cancelled'
            ]
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    actions = [
        'enable_reminders_for_selected',
        'disable_reminders_for_selected',
        'send_test_reminders',
    ]
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('user')
    
    def user_display(self, obj):
        """Display user with link."""
        url = reverse('admin:core_user_change', args=[obj.user.pk])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.user.get_full_name() or obj.user.username
        )
    user_display.short_description = 'User'
    user_display.admin_order_field = 'user__first_name'
    
    def enable_reminders_for_selected(self, request, queryset):
        """Enable reminders for selected users."""
        count = queryset.update(enable_reminders=True)
        self.message_user(request, f'Enabled reminders for {count} users.')
    enable_reminders_for_selected.short_description = 'Enable reminders'
    
    def disable_reminders_for_selected(self, request, queryset):
        """Disable reminders for selected users."""
        count = queryset.update(enable_reminders=False)
        self.message_user(request, f'Disabled reminders for {count} users.')
    disable_reminders_for_selected.short_description = 'Disable reminders'
    
    def send_test_reminders(self, request, queryset):
        """Send test reminders to selected users."""
        from .tasks import test_risk_action_reminder_configuration
        
        sent_count = 0
        for config in queryset:
            test_risk_action_reminder_configuration.delay(config.user.id)
            sent_count += 1
        
        self.message_user(
            request,
            f'Queued {sent_count} test reminders for sending.'
        )
    send_test_reminders.short_description = 'Send test reminders'


class RiskAnalyticsDashboard:
    """
    Custom admin dashboard section for risk analytics and reporting.
    
    This provides quick access to risk analytics data within the Django admin interface,
    allowing administrators to monitor risk metrics without needing separate dashboard access.
    """
    
    @staticmethod
    def get_admin_dashboard_data():
        """Get simplified analytics data for admin dashboard display."""
        from .analytics import RiskAnalyticsService
        
        try:
            # Get basic overview stats
            risk_overview = RiskAnalyticsService.get_risk_overview_stats()
            action_overview = RiskAnalyticsService.get_risk_action_overview_stats()
            
            # Simplified data for admin display
            return {
                'total_risks': risk_overview.get('total_risks', 0),
                'active_risks': risk_overview.get('active_risks', 0),
                'critical_high_risks': (
                    risk_overview.get('risk_level_distribution', {}).get('critical', 0) +
                    risk_overview.get('risk_level_distribution', {}).get('high', 0)
                ),
                'overdue_reviews': risk_overview.get('overdue_reviews', 0),
                'total_actions': action_overview.get('total_actions', 0),
                'overdue_actions': action_overview.get('overdue_actions', 0),
                'completion_rate': action_overview.get('completion_rate', 0),
                'avg_risk_score': risk_overview.get('average_risk_score', 0)
            }
        except Exception:
            # Return safe defaults if analytics fail
            return {
                'total_risks': 0,
                'active_risks': 0,
                'critical_high_risks': 0,
                'overdue_reviews': 0,
                'total_actions': 0,
                'overdue_actions': 0,
                'completion_rate': 0,
                'avg_risk_score': 0
            }
    
    @classmethod
    def admin_dashboard_html(cls):
        """Generate HTML dashboard widget for admin interface."""
        data = cls.get_admin_dashboard_data()
        
        return format_html(
            """
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0;">
                <h3 style="margin-top: 0; color: #495057;">Risk Analytics Dashboard</h3>
                <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                    <div style="flex: 1; min-width: 200px;">
                        <h4 style="margin-bottom: 5px; color: #6c757d; font-size: 12px; text-transform: uppercase;">Risk Overview</h4>
                        <p style="margin: 5px 0; font-size: 14px;"><strong>Total Risks:</strong> {}</p>
                        <p style="margin: 5px 0; font-size: 14px;"><strong>Active Risks:</strong> {}</p>
                        <p style="margin: 5px 0; font-size: 14px;"><strong>High/Critical:</strong> <span style="color: #dc3545;">{}</span></p>
                        <p style="margin: 5px 0; font-size: 14px;"><strong>Overdue Reviews:</strong> <span style="color: #fd7e14;">{}</span></p>
                    </div>
                    <div style="flex: 1; min-width: 200px;">
                        <h4 style="margin-bottom: 5px; color: #6c757d; font-size: 12px; text-transform: uppercase;">Action Progress</h4>
                        <p style="margin: 5px 0; font-size: 14px;"><strong>Total Actions:</strong> {}</p>
                        <p style="margin: 5px 0; font-size: 14px;"><strong>Completion Rate:</strong> <span style="color: #28a745;">{}%</span></p>
                        <p style="margin: 5px 0; font-size: 14px;"><strong>Overdue Actions:</strong> <span style="color: #dc3545;">{}</span></p>
                        <p style="margin: 5px 0; font-size: 14px;"><strong>Avg Risk Score:</strong> {}</p>
                    </div>
                </div>
                <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #dee2e6;">
                    <p style="margin: 0; font-size: 12px; color: #6c757d;">
                        📊 <strong>Full Analytics:</strong> Access comprehensive risk analytics via API at <code>/api/risk/analytics/dashboard/</code>
                        <br>
                        🔄 <strong>Real-time Data:</strong> Dashboard updates reflect current risk and action status
                    </p>
                </div>
            </div>
            """,
            data['total_risks'],
            data['active_risks'], 
            data['critical_high_risks'],
            data['overdue_reviews'],
            data['total_actions'],
            round(data['completion_rate'], 1),
            data['overdue_actions'],
            round(data['avg_risk_score'], 1)
        )


# Enhance existing Risk admin with analytics integration
def enhance_risk_admin_with_analytics(risk_admin_class):
    """Enhance existing RiskAdmin with analytics dashboard."""
    
    original_changelist_view = risk_admin_class.changelist_view
    
    def enhanced_changelist_view(self, request, extra_context=None):
        """Enhanced changelist with analytics dashboard."""
        extra_context = extra_context or {}
        extra_context['analytics_dashboard'] = RiskAnalyticsDashboard.admin_dashboard_html()
        return original_changelist_view(self, request, extra_context)
    
    risk_admin_class.changelist_view = enhanced_changelist_view
    return risk_admin_class


# Apply analytics enhancement to RiskAdmin
try:
    # Get the existing RiskAdmin class
    risk_admin = admin.site._registry.get(Risk)
    if risk_admin:
        enhance_risk_admin_with_analytics(risk_admin.__class__)
except Exception:
    # If enhancement fails, continue without analytics dashboard
    pass


# Analytics admin template enhancement
admin.site.site_header = "GRC Risk Management"
admin.site.site_title = "Risk Analytics & Management"
admin.site.index_title = "Risk Management Dashboard"