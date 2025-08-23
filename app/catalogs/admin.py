from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils import timezone
from .models import (
    Framework, Clause, Control, ControlEvidence, FrameworkMapping, 
    ControlAssessment, AssessmentEvidence, AssessmentReminderConfiguration, 
    AssessmentReminderLog
)


@admin.register(Framework)
class FrameworkAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'short_name', 'version', 'framework_type', 'status', 
        'is_mandatory', 'clause_count_display', 'issuing_organization', 'effective_date'
    ]
    list_filter = [
        'framework_type', 'status', 'is_mandatory', 'effective_date'
    ]
    search_fields = [
        'name', 'short_name', 'description', 'issuing_organization', 'external_id'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'clause_count_display', 'control_count_display',
        'import_checksum'
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'short_name', 'version', 'description', 'framework_type')
        }),
        ('Framework Details', {
            'fields': ('external_id', 'issuing_organization', 'official_url')
        }),
        ('Lifecycle Management', {
            'fields': ('effective_date', 'expiry_date', 'status', 'is_mandatory')
        }),
        ('Import Information', {
            'fields': ('imported_from', 'import_checksum'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at', 'clause_count_display', 'control_count_display'),
            'classes': ('collapse',)
        })
    )
    
    def clause_count_display(self, obj):
        count = obj.clause_count
        if count > 0:
            url = reverse('admin:catalogs_clause_changelist') + f'?framework__id__exact={obj.id}'
            return format_html('<a href="{}">{} clauses</a>', url, count)
        return '0 clauses'
    clause_count_display.short_description = 'Clauses'
    
    def control_count_display(self, obj):
        count = obj.control_count
        return f'{count} controls'
    control_count_display.short_description = 'Controls'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')


class ClauseInline(admin.TabularInline):
    model = Clause
    extra = 0
    fields = ['clause_id', 'title', 'clause_type', 'criticality', 'is_testable', 'sort_order']
    readonly_fields = ['control_count']
    show_change_link = True
    
    def control_count(self, obj):
        if obj.pk:
            return obj.control_count
        return 0


@admin.register(Clause)
class ClauseAdmin(admin.ModelAdmin):
    list_display = [
        'framework', 'clause_id', 'title', 'clause_type', 'criticality', 
        'is_testable', 'control_count_display', 'sort_order'
    ]
    list_filter = [
        'framework__name', 'clause_type', 'criticality', 'is_testable', 
        'framework__framework_type'
    ]
    search_fields = [
        'clause_id', 'title', 'description', 'framework__name', 'framework__short_name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'control_count_display', 'full_clause_id_display']
    raw_id_fields = ['framework', 'parent_clause']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('framework', 'clause_id', 'full_clause_id_display', 'title', 'description')
        }),
        ('Organization', {
            'fields': ('parent_clause', 'sort_order')
        }),
        ('Properties', {
            'fields': ('clause_type', 'criticality', 'is_testable')
        }),
        ('Implementation Guidance', {
            'fields': ('implementation_guidance', 'testing_procedures'),
            'classes': ('collapse',)
        }),
        ('External References', {
            'fields': ('external_references',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'control_count_display'),
            'classes': ('collapse',)
        })
    )
    
    def control_count_display(self, obj):
        count = obj.control_count
        if count > 0:
            url = reverse('admin:catalogs_control_changelist') + f'?clauses__id__exact={obj.id}'
            return format_html('<a href="{}">{} controls</a>', url, count)
        return '0 controls'
    control_count_display.short_description = 'Controls'
    
    def full_clause_id_display(self, obj):
        return obj.full_clause_id
    full_clause_id_display.short_description = 'Full Clause ID'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('framework', 'parent_clause')


class ControlEvidenceInline(admin.TabularInline):
    model = ControlEvidence
    extra = 0
    fields = ['title', 'evidence_type', 'evidence_date', 'is_validated', 'collected_by']
    readonly_fields = ['created_at']
    raw_id_fields = ['document', 'collected_by', 'validated_by']


@admin.register(Control)
class ControlAdmin(admin.ModelAdmin):
    list_display = [
        'control_id', 'name', 'control_type', 'automation_level', 'status',
        'control_owner', 'effectiveness_rating', 'last_tested_date', 'needs_testing_display'
    ]
    list_filter = [
        'control_type', 'automation_level', 'status', 'effectiveness_rating',
        'last_test_result', 'risk_rating'
    ]
    search_fields = [
        'control_id', 'name', 'description', 'business_owner'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'needs_testing_display', 'framework_coverage_display',
        'is_active'
    ]
    raw_id_fields = ['control_owner', 'created_by']
    filter_horizontal = ['clauses']
    inlines = [ControlEvidenceInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('control_id', 'name', 'description', 'clauses')
        }),
        ('Control Properties', {
            'fields': ('control_type', 'automation_level', 'status')
        }),
        ('Ownership & Responsibility', {
            'fields': ('control_owner', 'business_owner')
        }),
        ('Implementation', {
            'fields': ('implementation_details', 'frequency', 'evidence_requirements'),
            'classes': ('collapse',)
        }),
        ('Effectiveness & Testing', {
            'fields': (
                'last_tested_date', 'last_test_result', 'effectiveness_rating',
                'needs_testing_display'
            )
        }),
        ('Risk & Remediation', {
            'fields': ('risk_rating', 'remediation_plan'),
            'classes': ('collapse',)
        }),
        ('Documentation', {
            'fields': ('documentation_links',),
            'classes': ('collapse',)
        }),
        ('Version Control', {
            'fields': ('version', 'change_log'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at', 'framework_coverage_display', 'is_active'),
            'classes': ('collapse',)
        })
    )
    
    def needs_testing_display(self, obj):
        if obj.needs_testing:
            return format_html('<span style="color: red; font-weight: bold;">⚠ Needs Testing</span>')
        return format_html('<span style="color: green;">✓ Up to Date</span>')
    needs_testing_display.short_description = 'Testing Status'
    
    def framework_coverage_display(self, obj):
        frameworks = obj.framework_coverage
        if frameworks:
            framework_names = [f.short_name for f in frameworks]
            return ', '.join(framework_names)
        return 'No framework coverage'
    framework_coverage_display.short_description = 'Frameworks'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'control_owner', 'created_by'
        ).prefetch_related('clauses__framework')


@admin.register(ControlEvidence)
class ControlEvidenceAdmin(admin.ModelAdmin):
    list_display = [
        'control', 'title', 'evidence_type', 'evidence_date', 
        'is_validated', 'collected_by', 'created_at'
    ]
    list_filter = [
        'evidence_type', 'is_validated', 'evidence_date', 'created_at'
    ]
    search_fields = [
        'title', 'description', 'control__control_id', 'control__name'
    ]
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['control', 'document', 'collected_by', 'validated_by']
    date_hierarchy = 'evidence_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('control', 'title', 'evidence_type', 'description')
        }),
        ('Evidence Source', {
            'fields': ('document', 'external_url', 'evidence_date', 'collected_by')
        }),
        ('Validation', {
            'fields': ('is_validated', 'validated_by', 'validated_at', 'validation_notes')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'control', 'collected_by', 'validated_by', 'document'
        )


@admin.register(FrameworkMapping)
class FrameworkMappingAdmin(admin.ModelAdmin):
    list_display = [
        'source_clause', 'target_clause', 'mapping_type', 
        'confidence_level', 'created_by', 'verified_by'
    ]
    list_filter = [
        'mapping_type', 'confidence_level', 
        'source_clause__framework__name', 'target_clause__framework__name'
    ]
    search_fields = [
        'source_clause__clause_id', 'target_clause__clause_id',
        'source_clause__title', 'target_clause__title',
        'mapping_rationale'
    ]
    readonly_fields = ['created_at', 'verified_at']
    raw_id_fields = ['source_clause', 'target_clause', 'created_by', 'verified_by']
    
    fieldsets = (
        ('Mapping Details', {
            'fields': ('source_clause', 'target_clause', 'mapping_type')
        }),
        ('Analysis', {
            'fields': ('mapping_rationale', 'confidence_level')
        }),
        ('Verification', {
            'fields': ('created_by', 'created_at', 'verified_by', 'verified_at')
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'source_clause__framework', 'target_clause__framework',
            'created_by', 'verified_by'
        )


class AssessmentEvidenceInline(admin.TabularInline):
    model = AssessmentEvidence
    extra = 0
    fields = ['evidence', 'evidence_purpose', 'is_primary_evidence']
    raw_id_fields = ['evidence']
    show_change_link = True


@admin.register(ControlAssessment)
class ControlAssessmentAdmin(admin.ModelAdmin):
    list_display = [
        'assessment_id', 'control_id_display', 'control_name_display', 
        'applicability', 'status', 'implementation_status', 'assigned_to',
        'due_date', 'is_overdue_display', 'completion_percentage', 'risk_rating'
    ]
    list_filter = [
        'applicability', 'status', 'implementation_status', 'risk_rating',
        'maturity_level', 'control__clauses__framework__name',
        ('due_date', admin.DateFieldListFilter),
        ('assigned_to', admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = [
        'assessment_id', 'control__control_id', 'control__name',
        'assessment_notes', 'current_state_description'
    ]
    readonly_fields = [
        'assessment_id', 'created_at', 'updated_at', 'started_date', 
        'completed_date', 'is_overdue_display', 'completion_percentage',
        'days_until_due_display', 'change_log_display'
    ]
    raw_id_fields = ['control', 'assigned_to', 'reviewer', 'remediation_owner', 'created_by']
    inlines = [AssessmentEvidenceInline]
    date_hierarchy = 'due_date'
    
    fieldsets = (
        ('Assessment Overview', {
            'fields': ('assessment_id', 'control', 'applicability', 'applicability_rationale')
        }),
        ('Status & Progress', {
            'fields': ('status', 'implementation_status', 'completion_percentage', 'maturity_level')
        }),
        ('Assignment & Timeline', {
            'fields': ('assigned_to', 'reviewer', 'due_date', 'started_date', 'completed_date',
                      'is_overdue_display', 'days_until_due_display')
        }),
        ('Assessment Details', {
            'fields': ('current_state_description', 'target_state_description', 'gap_analysis',
                      'implementation_approach'),
            'classes': ('collapse',)
        }),
        ('Risk & Compliance', {
            'fields': ('risk_rating', 'compliance_score', 'assessment_notes', 'reviewer_comments')
        }),
        ('Remediation Planning', {
            'fields': ('remediation_plan', 'remediation_due_date', 'remediation_owner'),
            'classes': ('collapse',)
        }),
        ('Version Control', {
            'fields': ('version', 'change_log_display'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def control_id_display(self, obj):
        return obj.control.control_id
    control_id_display.short_description = 'Control ID'
    control_id_display.admin_order_field = 'control__control_id'
    
    def control_name_display(self, obj):
        return obj.control.name
    control_name_display.short_description = 'Control Name'
    control_name_display.admin_order_field = 'control__name'
    
    def is_overdue_display(self, obj):
        if obj.is_overdue:
            return format_html('<span style="color: red; font-weight: bold;">⚠ Overdue</span>')
        elif obj.days_until_due is not None and obj.days_until_due <= 7:
            return format_html('<span style="color: orange;">⏰ Due Soon</span>')
        return format_html('<span style="color: green;">✓ On Track</span>')
    is_overdue_display.short_description = 'Due Status'
    
    def days_until_due_display(self, obj):
        days = obj.days_until_due
        if days is None:
            return 'No due date'
        elif days < 0:
            return f'{abs(days)} days overdue'
        elif days == 0:
            return 'Due today'
        else:
            return f'{days} days remaining'
    days_until_due_display.short_description = 'Days Until Due'
    
    def change_log_display(self, obj):
        if not obj.change_log:
            return 'No changes logged'
        
        log_html = '<ul style="margin: 0; padding-left: 20px;">'
        for entry in obj.change_log[-5:]:  # Show last 5 entries
            log_html += f'<li><strong>{entry.get("user", "Unknown")}</strong> ({entry.get("timestamp", "Unknown time")}): {entry.get("description", "No description")}</li>'
        log_html += '</ul>'
        
        if len(obj.change_log) > 5:
            log_html += f'<p><em>... and {len(obj.change_log) - 5} more entries</em></p>'
        
        return mark_safe(log_html)
    change_log_display.short_description = 'Recent Changes'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'control', 'assigned_to', 'reviewer', 'remediation_owner', 'created_by'
        ).prefetch_related('evidence_links')
    
    actions = [
        'mark_as_complete', 'mark_as_in_progress', 'bulk_assign_due_date',
        'send_immediate_reminders', 'send_overdue_reminders'
    ]
    
    def mark_as_complete(self, request, queryset):
        updated = 0
        for assessment in queryset:
            if assessment.status != 'complete':
                assessment.update_status('complete', request.user, 'Bulk updated via admin')
                updated += 1
        
        self.message_user(request, f'Successfully marked {updated} assessments as complete.')
    mark_as_complete.short_description = 'Mark selected assessments as complete'
    
    def mark_as_in_progress(self, request, queryset):
        updated = 0
        for assessment in queryset:
            if assessment.status not in ['in_progress', 'complete']:
                assessment.update_status('in_progress', request.user, 'Bulk updated via admin')
                updated += 1
        
        self.message_user(request, f'Successfully marked {updated} assessments as in progress.')
    mark_as_in_progress.short_description = 'Mark selected assessments as in progress'
    
    def bulk_assign_due_date(self, request, queryset):
        # This would typically open a form to get the due date
        # For now, we'll set it to 30 days from today
        from django.utils import timezone
        due_date = timezone.now().date() + timezone.timedelta(days=30)
        
        updated = queryset.filter(due_date__isnull=True).update(due_date=due_date)
        self.message_user(request, f'Set due date to {due_date} for {updated} assessments.')
    bulk_assign_due_date.short_description = 'Set due date (30 days from today) for assessments without one'
    
    def send_immediate_reminders(self, request, queryset):
        """Send immediate reminders for selected assessments."""
        from .tasks import send_bulk_assessment_reminders
        
        # Filter assessments that have assigned users
        valid_assessments = queryset.filter(assigned_to__isnull=False)
        assessment_ids = list(valid_assessments.values_list('id', flat=True))
        
        if not assessment_ids:
            self.message_user(request, 'No assessments with assigned users selected.', level='WARNING')
            return
        
        try:
            send_bulk_assessment_reminders.delay(assessment_ids, 'due_today')
            self.message_user(
                request,
                f'Queued immediate reminders for {len(assessment_ids)} assessments.'
            )
        except Exception as e:
            self.message_user(
                request,
                f'Failed to queue reminders: {str(e)}',
                level='ERROR'
            )
    send_immediate_reminders.short_description = 'Send immediate reminders for selected assessments'
    
    def send_overdue_reminders(self, request, queryset):
        """Send overdue reminders for selected assessments."""
        from .tasks import send_bulk_assessment_reminders
        
        # Filter to only overdue assessments with assigned users
        overdue_assessments = queryset.filter(
            assigned_to__isnull=False,
            due_date__lt=timezone.now().date(),
            status__in=['not_started', 'pending', 'in_progress', 'under_review']
        )
        assessment_ids = list(overdue_assessments.values_list('id', flat=True))
        
        if not assessment_ids:
            self.message_user(request, 'No overdue assessments with assigned users selected.', level='WARNING')
            return
        
        try:
            send_bulk_assessment_reminders.delay(assessment_ids, 'overdue')
            self.message_user(
                request,
                f'Queued overdue reminders for {len(assessment_ids)} assessments.'
            )
        except Exception as e:
            self.message_user(
                request,
                f'Failed to queue overdue reminders: {str(e)}',
                level='ERROR'
            )
    send_overdue_reminders.short_description = 'Send overdue reminders for selected assessments'


@admin.register(AssessmentEvidence)
class AssessmentEvidenceAdmin(admin.ModelAdmin):
    list_display = [
        'assessment', 'evidence_title', 'evidence_type_display', 'evidence_purpose',
        'is_primary_evidence', 'created_by', 'created_at'
    ]
    list_filter = [
        'is_primary_evidence', 'evidence__evidence_type', 'created_at',
        ('assessment__control__clauses__framework', admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = [
        'evidence_purpose', 'evidence__title', 'assessment__assessment_id',
        'assessment__control__control_id'
    ]
    readonly_fields = ['created_at']
    raw_id_fields = ['assessment', 'evidence', 'created_by']
    date_hierarchy = 'created_at'
    actions = ['mark_as_primary_evidence', 'remove_primary_evidence_flag']
    
    def mark_as_primary_evidence(self, request, queryset):
        """Mark selected evidence as primary for their assessments."""
        count = 0
        for evidence_link in queryset:
            # First, unmark any existing primary evidence for this assessment
            AssessmentEvidence.objects.filter(
                assessment=evidence_link.assessment,
                is_primary_evidence=True
            ).update(is_primary_evidence=False)
            
            # Then mark this one as primary
            evidence_link.is_primary_evidence = True
            evidence_link.save()
            count += 1
        
        self.message_user(request, f'{count} evidence items marked as primary.')
    mark_as_primary_evidence.short_description = 'Mark as primary evidence'
    
    def remove_primary_evidence_flag(self, request, queryset):
        """Remove primary evidence flag from selected items."""
        count = queryset.update(is_primary_evidence=False)
        self.message_user(request, f'{count} evidence items unmarked as primary.')
    remove_primary_evidence_flag.short_description = 'Remove primary evidence flag'
    
    def evidence_title(self, obj):
        return obj.evidence.title
    evidence_title.short_description = 'Evidence Title'
    evidence_title.admin_order_field = 'evidence__title'
    
    def evidence_type_display(self, obj):
        return obj.evidence.get_evidence_type_display()
    evidence_type_display.short_description = 'Evidence Type'
    evidence_type_display.admin_order_field = 'evidence__evidence_type'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'assessment__control', 'evidence', 'created_by'
        )


@admin.register(AssessmentReminderConfiguration)
class AssessmentReminderConfigurationAdmin(admin.ModelAdmin):
    """Admin interface for managing assessment reminder configurations."""
    
    list_display = [
        'user_display',
        'enable_reminders',
        'advance_warning_days',
        'reminder_frequency',
        'email_notifications',
        'weekly_digest_enabled',
        'last_updated'
    ]
    
    list_filter = [
        'enable_reminders',
        'email_notifications',
        'reminder_frequency',
        'weekly_digest_enabled',
        'overdue_reminders',
        'created_at'
    ]
    
    search_fields = [
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name'
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = [
        ('User Information', {
            'fields': ['user']
        }),
        ('Reminder Settings', {
            'fields': [
                'enable_reminders',
                'advance_warning_days',
                'overdue_reminders',
                'reminder_frequency',
                'custom_reminder_days'
            ]
        }),
        ('Email Preferences', {
            'fields': [
                'email_notifications',
                'include_assessment_details',
                'include_remediation_items'
            ]
        }),
        ('Digest Settings', {
            'fields': [
                'daily_digest_enabled',
                'weekly_digest_enabled',
                'digest_day_of_week'
            ]
        }),
        ('Auto-silence Settings', {
            'fields': [
                'silence_completed_assessments',
                'silence_not_applicable'
            ]
        }),
        ('Metadata', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    actions = [
        'enable_reminders_bulk',
        'disable_reminders_bulk',
        'test_reminder_configuration',
        'send_immediate_digest'
    ]
    
    def user_display(self, obj):
        """Display user with email."""
        return f"{obj.user.get_full_name() or obj.user.username} ({obj.user.email})"
    user_display.short_description = 'User'
    user_display.admin_order_field = 'user__username'
    
    def last_updated(self, obj):
        """Display last updated time."""
        return obj.updated_at.strftime("%Y-%m-%d %H:%M")
    last_updated.short_description = 'Last Updated'
    last_updated.admin_order_field = 'updated_at'
    
    def enable_reminders_bulk(self, request, queryset):
        """Enable reminders for selected users."""
        count = queryset.update(enable_reminders=True, email_notifications=True)
        self.message_user(request, f'Enabled reminders for {count} users.')
    enable_reminders_bulk.short_description = 'Enable reminders for selected users'
    
    def disable_reminders_bulk(self, request, queryset):
        """Disable reminders for selected users."""
        count = queryset.update(enable_reminders=False)
        self.message_user(request, f'Disabled reminders for {count} users.')
    disable_reminders_bulk.short_description = 'Disable reminders for selected users'
    
    def test_reminder_configuration(self, request, queryset):
        """Send test reminder to selected users."""
        from .tasks import test_reminder_configuration
        
        sent_count = 0
        for config in queryset:
            try:
                test_reminder_configuration.delay(config.user.id)
                sent_count += 1
            except Exception as e:
                self.message_user(
                    request, 
                    f'Failed to queue test for {config.user.username}: {str(e)}',
                    level='ERROR'
                )
        
        self.message_user(request, f'Queued test reminders for {sent_count} users.')
    test_reminder_configuration.short_description = 'Send test reminder to selected users'
    
    def send_immediate_digest(self, request, queryset):
        """Send immediate weekly digest to selected users."""
        from .notifications import AssessmentReminderService
        
        sent_count = 0
        failed_count = 0
        
        for config in queryset:
            try:
                success = AssessmentReminderService.send_weekly_digest(config.user)
                if success:
                    sent_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                self.message_user(
                    request,
                    f'Failed to send digest to {config.user.username}: {str(e)}',
                    level='ERROR'
                )
        
        self.message_user(
            request, 
            f'Sent digests to {sent_count} users, {failed_count} failed.'
        )
    send_immediate_digest.short_description = 'Send immediate weekly digest'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(AssessmentReminderLog)
class AssessmentReminderLogAdmin(admin.ModelAdmin):
    """Admin interface for viewing assessment reminder logs."""
    
    list_display = [
        'sent_at',
        'user_display',
        'assessment_display',
        'reminder_type',
        'days_before_due',
        'email_sent_display'
    ]
    
    list_filter = [
        'reminder_type',
        'email_sent',
        'sent_at',
        'days_before_due'
    ]
    
    search_fields = [
        'user__username',
        'user__email',
        'assessment__assessment_id',
        'assessment__control__control_id'
    ]
    
    readonly_fields = [
        'assessment',
        'user',
        'reminder_type',
        'days_before_due',
        'sent_at',
        'email_sent'
    ]
    
    date_hierarchy = 'sent_at'
    
    actions = [
        'mark_as_sent',
        'mark_as_failed'
    ]
    
    def user_display(self, obj):
        """Display user info."""
        return f"{obj.user.get_full_name() or obj.user.username}"
    user_display.short_description = 'User'
    user_display.admin_order_field = 'user__username'
    
    def assessment_display(self, obj):
        """Display assessment info."""
        return f"{obj.assessment.control.control_id} ({obj.assessment.assessment_id})"
    assessment_display.short_description = 'Assessment'
    assessment_display.admin_order_field = 'assessment__control__control_id'
    
    def email_sent_display(self, obj):
        """Display email sent status with color."""
        if obj.email_sent:
            return format_html('<span style="color: green;">✓ Sent</span>')
        else:
            return format_html('<span style="color: red;">✗ Failed</span>')
    email_sent_display.short_description = 'Email Status'
    email_sent_display.admin_order_field = 'email_sent'
    
    def mark_as_sent(self, request, queryset):
        """Mark selected logs as successfully sent."""
        count = queryset.update(email_sent=True)
        self.message_user(request, f'Marked {count} reminder logs as sent.')
    mark_as_sent.short_description = 'Mark as sent'
    
    def mark_as_failed(self, request, queryset):
        """Mark selected logs as failed."""
        count = queryset.update(email_sent=False)
        self.message_user(request, f'Marked {count} reminder logs as failed.')
    mark_as_failed.short_description = 'Mark as failed'
    
    def has_add_permission(self, request):
        """Disable adding reminder logs (they're created automatically)."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable changing reminder logs."""
        return False
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'assessment__control'
        )