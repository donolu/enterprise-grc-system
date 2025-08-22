from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Framework, Clause, Control, ControlEvidence, FrameworkMapping


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