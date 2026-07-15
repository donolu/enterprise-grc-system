from rest_framework import serializers

from .models import (
    GovernanceArtefact,
    ManagementReview,
    NonConformity,
    RegulatoryRequirement,
)


class GovernanceArtefactSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = GovernanceArtefact
        fields = [
            'id', 'artefact_id', 'title', 'artefact_type', 'description',
            'status', 'version', 'owner', 'owner_username', 'effective_date',
            'review_due_date', 'linked_frameworks', 'linked_controls',
            'linked_documents', 'source_template', 'metadata',
            'created_by_username', 'created_at', 'updated_at',
        ]
        read_only_fields = ['artefact_id', 'created_by_username', 'created_at', 'updated_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class RegulatoryRequirementSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = RegulatoryRequirement
        fields = [
            'id', 'requirement_id', 'title', 'source_type', 'issuing_body',
            'jurisdiction', 'reference', 'description', 'applicability_status',
            'compliance_status', 'priority', 'owner', 'owner_username',
            'next_review_date', 'linked_frameworks', 'linked_controls',
            'linked_risks', 'linked_documents', 'linked_artefacts',
            'metadata', 'created_by_username', 'created_at', 'updated_at',
        ]
        read_only_fields = ['requirement_id', 'created_by_username', 'created_at', 'updated_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class NonConformitySerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    raised_by_username = serializers.CharField(source='raised_by.username', read_only=True)
    is_overdue = serializers.ReadOnlyField()

    class Meta:
        model = NonConformity
        fields = [
            'id', 'nonconformity_id', 'title', 'description', 'severity',
            'status', 'source_type', 'detected_on', 'due_date', 'closed_on',
            'owner', 'owner_username', 'raised_by_username',
            'regulatory_requirement', 'root_cause', 'corrective_action',
            'preventive_action', 'verification_notes', 'linked_controls',
            'linked_risks', 'linked_documents', 'metadata', 'is_overdue',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'nonconformity_id', 'closed_on', 'raised_by_username',
            'is_overdue', 'created_at', 'updated_at',
        ]

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['raised_by'] = request.user
        return super().create(validated_data)


class ManagementReviewSerializer(serializers.ModelSerializer):
    chair_username = serializers.CharField(source='chair.username', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = ManagementReview
        fields = [
            'id', 'review_id', 'title', 'status', 'meeting_date',
            'period_start', 'period_end', 'chair', 'chair_username',
            'attendees', 'agenda', 'minutes', 'decisions', 'actions_summary',
            'inputs', 'outputs', 'linked_requirements',
            'linked_nonconformities', 'linked_artefacts', 'linked_controls',
            'linked_documents', 'created_by_username', 'created_at',
            'updated_at',
        ]
        read_only_fields = ['review_id', 'created_by_username', 'created_at', 'updated_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        return super().create(validated_data)
