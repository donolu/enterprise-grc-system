from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404

from .models import AssessmentReport
from .tasks import generate_assessment_report_task


@admin.register(AssessmentReport)
class AssessmentReportAdmin(admin.ModelAdmin):
    """Admin interface for AssessmentReport management."""
    
    list_display = [
        'title',
        'report_type_display',
        'framework_display',
        'status_display',
        'requested_by',
        'requested_at',
        'download_link'
    ]
    
    list_filter = [
        'report_type',
        'status',
        'framework',
        'requested_at',
        'include_evidence_summary',
        'include_implementation_notes'
    ]
    
    search_fields = [
        'title',
        'description',
        'requested_by__username',
        'requested_by__email',
        'framework__name'
    ]
    
    readonly_fields = [
        'requested_by',
        'requested_at',
        'status',
        'generation_started_at',
        'generation_completed_at',
        'error_message',
        'generated_file'
    ]
    
    fieldsets = [
        ('Report Information', {
            'fields': [
                'title',
                'description',
                'report_type',
                'framework'
            ]
        }),
        ('Report Configuration', {
            'fields': [
                'include_evidence_summary',
                'include_implementation_notes',
                'include_overdue_items',
                'include_charts'
            ]
        }),
        ('Generation Status', {
            'fields': [
                'status',
                'requested_by',
                'requested_at',
                'generation_started_at',
                'generation_completed_at',
                'error_message',
                'generated_file'
            ]
        })
    ]
    
    actions = [
        'generate_selected_reports',
        'mark_as_failed',
        'reset_to_pending'
    ]
    
    def report_type_display(self, obj):
        """Display report type with icon."""
        icons = {
            'assessment_summary': '📊',
            'detailed_assessment': '📋',
            'evidence_portfolio': '📁',
            'compliance_gap': '⚠️'
        }
        icon = icons.get(obj.report_type, '📄')
        return f"{icon} {obj.get_report_type_display()}"
    report_type_display.short_description = 'Report Type'
    
    def framework_display(self, obj):
        """Display framework name or 'Custom'."""
        if obj.framework:
            return f"{obj.framework.short_name} ({obj.framework.version})"
        return "Custom Selection"
    framework_display.short_description = 'Framework'
    
    def status_display(self, obj):
        """Display status with color coding."""
        colors = {
            'pending': '#6c757d',
            'processing': '#007bff', 
            'completed': '#28a745',
            'failed': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        
        status_text = obj.get_status_display()
        if obj.status == 'processing' and obj.generation_started_at:
            duration = timezone.now() - obj.generation_started_at
            minutes = int(duration.total_seconds() / 60)
            status_text += f" ({minutes}m)"
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            status_text
        )
    status_display.short_description = 'Status'
    
    def download_link(self, obj):
        """Display download link if report is completed."""
        if obj.status == 'completed' and obj.generated_file:
            url = reverse('admin:core_document_change', args=[obj.generated_file.pk])
            return format_html(
                '<a href="{}" target="_blank">📄 Download PDF</a>',
                url
            )
        elif obj.status == 'processing':
            return format_html('<span style="color: #007bff;">🔄 Generating...</span>')
        elif obj.status == 'failed':
            return format_html('<span style="color: #dc3545;">❌ Failed</span>')
        else:
            return format_html('<span style="color: #6c757d;">⏳ Pending</span>')
    download_link.short_description = 'Download'
    
    def generate_selected_reports(self, request, queryset):
        """Generate selected reports."""
        generated_count = 0
        already_processing = 0
        failed_count = 0
        
        for report in queryset:
            if report.status == 'processing':
                already_processing += 1
                continue
                
            if report.status == 'completed':
                # Allow regeneration of completed reports
                report.status = 'pending'
                report.generation_started_at = None
                report.generation_completed_at = None
                report.error_message = ''
                report.save()
            
            try:
                generate_assessment_report_task.delay(report.id)
                report.status = 'processing'
                report.generation_started_at = timezone.now()
                report.save()
                generated_count += 1
            except Exception as e:
                report.status = 'failed'
                report.error_message = f"Failed to queue generation: {str(e)}"
                report.save()
                failed_count += 1
        
        # Show summary message
        message_parts = []
        if generated_count:
            message_parts.append(f"{generated_count} report(s) queued for generation")
        if already_processing:
            message_parts.append(f"{already_processing} already processing")
        if failed_count:
            message_parts.append(f"{failed_count} failed to queue")
        
        if message_parts:
            self.message_user(request, ". ".join(message_parts))
        else:
            self.message_user(request, "No reports were processed", messages.WARNING)
    
    generate_selected_reports.short_description = "Generate selected reports"
    
    def mark_as_failed(self, request, queryset):
        """Mark selected reports as failed (for cleanup)."""
        updated = queryset.update(
            status='failed',
            error_message='Manually marked as failed by admin',
            generation_completed_at=timezone.now()
        )
        
        self.message_user(
            request,
            f"{updated} report(s) marked as failed"
        )
    mark_as_failed.short_description = "Mark as failed"
    
    def reset_to_pending(self, request, queryset):
        """Reset selected reports to pending status."""
        updated = queryset.update(
            status='pending',
            generation_started_at=None,
            generation_completed_at=None,
            error_message=''
        )
        
        self.message_user(
            request,
            f"{updated} report(s) reset to pending status"
        )
    reset_to_pending.short_description = "Reset to pending"
    
    def get_queryset(self, request):
        """Optimize queries with related data."""
        return super().get_queryset(request).select_related(
            'framework',
            'requested_by',
            'generated_file'
        )
    
    def has_add_permission(self, request):
        """Allow adding reports through admin."""
        return True
    
    def has_change_permission(self, request, obj=None):
        """Allow changing report configuration."""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Allow deleting reports."""
        return True
    
    def get_readonly_fields(self, request, obj=None):
        """Make certain fields readonly based on status."""
        readonly = list(self.readonly_fields)
        
        if obj and obj.status == 'processing':
            # Don't allow changing core settings while processing
            readonly.extend([
                'report_type',
                'framework',
                'title'
            ])
        
        return readonly
    
    def save_model(self, request, obj, form, change):
        """Set requested_by when creating new report."""
        if not change:  # Creating new report
            obj.requested_by = request.user
        super().save_model(request, obj, form, change)
    
    def response_change(self, request, obj):
        """Add generate button to change form."""
        if '_generate' in request.POST:
            if obj.status == 'processing':
                self.message_user(request, "Report is already being generated", messages.WARNING)
            else:
                try:
                    generate_assessment_report_task.delay(obj.id)
                    obj.status = 'processing'
                    obj.generation_started_at = timezone.now()
                    obj.save()
                    self.message_user(request, "Report generation started successfully")
                except Exception as e:
                    self.message_user(request, f"Failed to start generation: {str(e)}", messages.ERROR)
            
            return HttpResponseRedirect(request.path)
        
        return super().response_change(request, obj)
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Add custom buttons to change view."""
        extra_context = extra_context or {}
        
        try:
            obj = self.get_object(request, object_id)
            if obj:
                extra_context['show_generate_button'] = obj.status in ['pending', 'failed', 'completed']
                extra_context['is_processing'] = obj.status == 'processing'
        except:
            pass
        
        return super().change_view(request, object_id, form_url, extra_context)