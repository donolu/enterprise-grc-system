from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from .models import (
    GovernanceArtefact,
    ManagementReview,
    NonConformity,
    RegulatoryRequirement,
)
from .serializers import (
    GovernanceArtefactSerializer,
    ManagementReviewSerializer,
    NonConformitySerializer,
    RegulatoryRequirementSerializer,
)


class CompliancePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class GovernanceArtefactViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = GovernanceArtefactSerializer
    pagination_class = CompliancePagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['artefact_type', 'status', 'owner', 'linked_frameworks']
    search_fields = ['artefact_id', 'title', 'description']
    ordering_fields = ['artefact_id', 'title', 'artefact_type', 'review_due_date', 'updated_at']
    ordering = ['artefact_type', 'title']

    def get_queryset(self):
        return GovernanceArtefact.objects.select_related(
            'owner', 'created_by', 'source_template'
        ).prefetch_related('linked_frameworks', 'linked_controls', 'linked_documents')


class RegulatoryRequirementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RegulatoryRequirementSerializer
    pagination_class = CompliancePagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'source_type', 'applicability_status', 'compliance_status',
        'priority', 'owner', 'linked_frameworks',
    ]
    search_fields = [
        'requirement_id', 'title', 'issuing_body', 'jurisdiction',
        'reference', 'description',
    ]
    ordering_fields = ['requirement_id', 'title', 'priority', 'next_review_date', 'updated_at']
    ordering = ['priority', 'title']

    def get_queryset(self):
        return RegulatoryRequirement.objects.select_related('owner', 'created_by').prefetch_related(
            'linked_frameworks',
            'linked_controls',
            'linked_risks',
            'linked_documents',
            'linked_artefacts',
        )


class NonConformityViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = NonConformitySerializer
    pagination_class = CompliancePagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'severity', 'status', 'source_type', 'owner', 'regulatory_requirement',
    ]
    search_fields = [
        'nonconformity_id', 'title', 'description', 'root_cause',
        'corrective_action', 'preventive_action',
    ]
    ordering_fields = ['nonconformity_id', 'title', 'severity', 'due_date', 'detected_on', 'updated_at']
    ordering = ['-detected_on', 'title']

    def get_queryset(self):
        return NonConformity.objects.select_related(
            'owner', 'raised_by', 'regulatory_requirement'
        ).prefetch_related('linked_controls', 'linked_risks', 'linked_documents')


class ManagementReviewViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ManagementReviewSerializer
    pagination_class = CompliancePagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'chair', 'linked_requirements', 'linked_nonconformities']
    search_fields = ['review_id', 'title', 'agenda', 'minutes', 'decisions', 'actions_summary']
    ordering_fields = ['review_id', 'title', 'meeting_date', 'status', 'updated_at']
    ordering = ['-meeting_date', 'title']

    def get_queryset(self):
        return ManagementReview.objects.select_related('chair', 'created_by').prefetch_related(
            'attendees',
            'linked_requirements',
            'linked_nonconformities',
            'linked_artefacts',
            'linked_controls',
            'linked_documents',
        )
