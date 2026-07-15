from django.contrib import admin

from .models import (
    GovernanceArtefact,
    ManagementReview,
    NonConformity,
    RegulatoryRequirement,
)


@admin.register(GovernanceArtefact)
class GovernanceArtefactAdmin(admin.ModelAdmin):
    list_display = ['artefact_id', 'title', 'artefact_type', 'status', 'owner', 'review_due_date']
    list_filter = ['artefact_type', 'status', 'review_due_date']
    search_fields = ['artefact_id', 'title', 'description']
    raw_id_fields = ['owner', 'created_by', 'source_template']
    filter_horizontal = ['linked_frameworks', 'linked_controls', 'linked_documents']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(RegulatoryRequirement)
class RegulatoryRequirementAdmin(admin.ModelAdmin):
    list_display = [
        'requirement_id', 'title', 'source_type', 'applicability_status',
        'compliance_status', 'priority', 'owner', 'next_review_date',
    ]
    list_filter = [
        'source_type', 'applicability_status', 'compliance_status',
        'priority', 'next_review_date',
    ]
    search_fields = ['requirement_id', 'title', 'issuing_body', 'jurisdiction', 'reference']
    raw_id_fields = ['owner', 'created_by']
    filter_horizontal = [
        'linked_frameworks', 'linked_controls', 'linked_risks',
        'linked_documents', 'linked_artefacts',
    ]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(NonConformity)
class NonConformityAdmin(admin.ModelAdmin):
    list_display = [
        'nonconformity_id', 'title', 'severity', 'status',
        'source_type', 'owner', 'due_date', 'closed_on',
    ]
    list_filter = ['severity', 'status', 'source_type', 'due_date', 'closed_on']
    search_fields = ['nonconformity_id', 'title', 'description', 'root_cause']
    raw_id_fields = ['owner', 'raised_by', 'regulatory_requirement']
    filter_horizontal = ['linked_controls', 'linked_risks', 'linked_documents']
    readonly_fields = ['created_at', 'updated_at', 'is_overdue']


@admin.register(ManagementReview)
class ManagementReviewAdmin(admin.ModelAdmin):
    list_display = ['review_id', 'title', 'status', 'meeting_date', 'chair']
    list_filter = ['status', 'meeting_date']
    search_fields = ['review_id', 'title', 'agenda', 'minutes', 'decisions']
    raw_id_fields = ['chair', 'created_by']
    filter_horizontal = [
        'attendees', 'linked_requirements', 'linked_nonconformities',
        'linked_artefacts', 'linked_controls', 'linked_documents',
    ]
    readonly_fields = ['created_at', 'updated_at']
