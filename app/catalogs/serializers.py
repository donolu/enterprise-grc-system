from rest_framework import serializers
from .models import Framework, Clause, Control, ControlEvidence, FrameworkMapping, ControlAssessment, AssessmentEvidence
from django.contrib.auth import get_user_model

User = get_user_model()


class FrameworkListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for framework listings."""
    clause_count = serializers.ReadOnlyField()
    control_count = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    
    class Meta:
        model = Framework
        fields = [
            'id', 'name', 'short_name', 'version', 'framework_type', 
            'status', 'is_mandatory', 'effective_date', 'clause_count', 
            'control_count', 'is_active', 'issuing_organization'
        ]


class FrameworkDetailSerializer(serializers.ModelSerializer):
    """Detailed framework serializer with full information."""
    clause_count = serializers.ReadOnlyField()
    control_count = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Framework
        fields = [
            'id', 'name', 'short_name', 'version', 'description', 
            'framework_type', 'external_id', 'issuing_organization', 
            'official_url', 'effective_date', 'expiry_date', 'status', 
            'is_mandatory', 'clause_count', 'control_count', 'is_active',
            'created_by_username', 'created_at', 'updated_at',
            'imported_from', 'import_checksum'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'clause_count', 'control_count',
            'is_active', 'imported_from', 'import_checksum'
        ]


class ClauseListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for clause listings."""
    framework_name = serializers.CharField(source='framework.name', read_only=True)
    framework_short_name = serializers.CharField(source='framework.short_name', read_only=True)
    control_count = serializers.ReadOnlyField()
    full_clause_id = serializers.ReadOnlyField()
    
    class Meta:
        model = Clause
        fields = [
            'id', 'clause_id', 'full_clause_id', 'title', 'clause_type', 
            'criticality', 'is_testable', 'control_count', 'framework_name',
            'framework_short_name', 'sort_order'
        ]


class ClauseDetailSerializer(serializers.ModelSerializer):
    """Detailed clause serializer with full information."""
    framework_name = serializers.CharField(source='framework.name', read_only=True)
    framework_short_name = serializers.CharField(source='framework.short_name', read_only=True)
    control_count = serializers.ReadOnlyField()
    full_clause_id = serializers.ReadOnlyField()
    parent_clause_id = serializers.CharField(source='parent_clause.clause_id', read_only=True)
    subclauses = serializers.SerializerMethodField()
    
    class Meta:
        model = Clause
        fields = [
            'id', 'framework', 'framework_name', 'framework_short_name',
            'clause_id', 'full_clause_id', 'title', 'description',
            'parent_clause', 'parent_clause_id', 'sort_order', 'clause_type',
            'criticality', 'is_testable', 'implementation_guidance',
            'testing_procedures', 'external_references', 'control_count',
            'subclauses', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'control_count', 'full_clause_id', 'subclauses', 
            'created_at', 'updated_at'
        ]
    
    def get_subclauses(self, obj):
        subclauses = obj.subclauses.all()
        return ClauseListSerializer(subclauses, many=True).data


class ControlEvidenceSerializer(serializers.ModelSerializer):
    """Serializer for control evidence."""
    collected_by_username = serializers.CharField(source='collected_by.username', read_only=True)
    validated_by_username = serializers.CharField(source='validated_by.username', read_only=True)
    document_url = serializers.CharField(source='document.file_url', read_only=True)
    document_name = serializers.CharField(source='document.file_name', read_only=True)
    
    class Meta:
        model = ControlEvidence
        fields = [
            'id', 'title', 'evidence_type', 'description', 'document',
            'document_url', 'document_name', 'external_url', 'evidence_date',
            'collected_by', 'collected_by_username', 'is_validated',
            'validated_by', 'validated_by_username', 'validated_at',
            'validation_notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'validated_at', 'created_at', 'updated_at',
            'document_url', 'document_name'
        ]


class ControlListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for control listings."""
    control_owner_name = serializers.CharField(source='control_owner.get_full_name', read_only=True)
    framework_coverage = serializers.SerializerMethodField()
    is_active = serializers.ReadOnlyField()
    needs_testing = serializers.ReadOnlyField()
    clause_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Control
        fields = [
            'id', 'control_id', 'name', 'control_type', 'automation_level',
            'status', 'control_owner_name', 'effectiveness_rating',
            'last_tested_date', 'risk_rating', 'is_active', 'needs_testing',
            'framework_coverage', 'clause_count', 'version'
        ]
    
    def get_framework_coverage(self, obj):
        frameworks = obj.framework_coverage
        return [{'id': f.id, 'short_name': f.short_name, 'name': f.name} for f in frameworks]
    
    def get_clause_count(self, obj):
        return obj.clauses.count()


class ControlDetailSerializer(serializers.ModelSerializer):
    """Detailed control serializer with full information."""
    control_owner_name = serializers.CharField(source='control_owner.get_full_name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    framework_coverage = serializers.SerializerMethodField()
    is_active = serializers.ReadOnlyField()
    needs_testing = serializers.ReadOnlyField()
    evidence = ControlEvidenceSerializer(many=True, read_only=True)
    clauses_detail = ClauseListSerializer(source='clauses', many=True, read_only=True)
    
    class Meta:
        model = Control
        fields = [
            'id', 'control_id', 'name', 'description', 'clauses', 'clauses_detail',
            'control_type', 'automation_level', 'status', 'control_owner',
            'control_owner_name', 'business_owner', 'implementation_details',
            'frequency', 'last_tested_date', 'last_test_result',
            'effectiveness_rating', 'evidence_requirements', 'documentation_links',
            'risk_rating', 'remediation_plan', 'version', 'change_log',
            'is_active', 'needs_testing', 'framework_coverage', 'evidence',
            'created_by_username', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'is_active', 'needs_testing', 'framework_coverage', 
            'created_at', 'updated_at'
        ]
    
    def get_framework_coverage(self, obj):
        frameworks = obj.framework_coverage
        return [{'id': f.id, 'short_name': f.short_name, 'name': f.name} for f in frameworks]


class ControlCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating controls."""
    
    class Meta:
        model = Control
        fields = [
            'control_id', 'name', 'description', 'clauses', 'control_type',
            'automation_level', 'status', 'control_owner', 'business_owner',
            'implementation_details', 'frequency', 'last_tested_date',
            'last_test_result', 'effectiveness_rating', 'evidence_requirements',
            'documentation_links', 'risk_rating', 'remediation_plan', 'version'
        ]
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Add change log entry if significant fields changed
        significant_fields = [
            'name', 'description', 'status', 'control_owner', 
            'effectiveness_rating', 'implementation_details'
        ]
        
        changes = []
        for field in significant_fields:
            if field in validated_data and getattr(instance, field) != validated_data[field]:
                old_value = getattr(instance, field)
                new_value = validated_data[field]
                changes.append(f'{field}: "{old_value}" → "{new_value}"')
        
        if changes:
            user = self.context['request'].user
            change_description = f'Updated: {", ".join(changes)}'
            instance.add_change_log_entry(user, change_description)
        
        return super().update(instance, validated_data)


class FrameworkMappingSerializer(serializers.ModelSerializer):
    """Serializer for framework mappings."""
    source_clause_display = serializers.CharField(source='source_clause.__str__', read_only=True)
    target_clause_display = serializers.CharField(source='target_clause.__str__', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    verified_by_username = serializers.CharField(source='verified_by.username', read_only=True)
    
    class Meta:
        model = FrameworkMapping
        fields = [
            'id', 'source_clause', 'source_clause_display', 'target_clause',
            'target_clause_display', 'mapping_type', 'mapping_rationale',
            'confidence_level', 'created_by_username', 'created_at',
            'verified_by_username', 'verified_at'
        ]
        read_only_fields = [
            'created_at', 'verified_at', 'source_clause_display', 
            'target_clause_display'
        ]


class FrameworkStatsSerializer(serializers.Serializer):
    """Serializer for framework statistics."""
    total_frameworks = serializers.IntegerField()
    active_frameworks = serializers.IntegerField()
    total_clauses = serializers.IntegerField()
    total_controls = serializers.IntegerField()
    active_controls = serializers.IntegerField()
    controls_needing_testing = serializers.IntegerField()
    framework_types = serializers.DictField()
    control_effectiveness = serializers.DictField()


class ControlTestingSerializer(serializers.Serializer):
    """Serializer for updating control testing results."""
    test_date = serializers.DateField()
    test_result = serializers.ChoiceField(choices=Control.EFFECTIVENESS_RATINGS)
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    
    def update_control_testing(self, control):
        """Update control with testing results."""
        control.last_tested_date = self.validated_data['test_date']
        control.last_test_result = self.validated_data['test_result']
        control.effectiveness_rating = self.validated_data['test_result']
        control.save()
        
        # Add change log entry
        user = self.context['request'].user
        notes = self.validated_data.get('notes', '')
        change_description = f'Control tested on {control.last_tested_date}. Result: {control.get_last_test_result_display()}'
        if notes:
            change_description += f'. Notes: {notes}'
        
        control.add_change_log_entry(user, change_description)
        
        return control


class ControlAssessmentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for assessment listings."""
    control_id = serializers.CharField(source='control.control_id', read_only=True)
    control_name = serializers.CharField(source='control.name', read_only=True)
    framework_name = serializers.CharField(source='control.clauses.first.framework.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.get_full_name', read_only=True)
    is_overdue = serializers.ReadOnlyField()
    is_complete = serializers.ReadOnlyField()
    completion_percentage = serializers.ReadOnlyField()
    days_until_due = serializers.ReadOnlyField()
    evidence_count = serializers.SerializerMethodField()
    has_primary_evidence = serializers.SerializerMethodField()
    
    def get_evidence_count(self, obj):
        """Get count of evidence linked to this assessment."""
        return obj.evidence_links.count()
    
    def get_has_primary_evidence(self, obj):
        """Check if assessment has primary evidence."""
        return obj.evidence_links.filter(is_primary_evidence=True).exists()
    
    class Meta:
        model = ControlAssessment
        fields = [
            'id', 'assessment_id', 'control_id', 'control_name', 'framework_name',
            'applicability', 'status', 'implementation_status', 'assigned_to_name',
            'reviewer_name', 'due_date', 'completion_percentage', 'is_overdue',
            'is_complete', 'days_until_due', 'risk_rating', 'compliance_score',
            'evidence_count', 'has_primary_evidence', 'created_at', 'updated_at'
        ]


class ControlAssessmentDetailSerializer(serializers.ModelSerializer):
    """Detailed assessment serializer with full information."""
    control_details = ControlListSerializer(source='control', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.get_full_name', read_only=True)
    remediation_owner_name = serializers.CharField(source='remediation_owner.get_full_name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    # Computed properties
    is_overdue = serializers.ReadOnlyField()
    is_complete = serializers.ReadOnlyField()
    completion_percentage = serializers.ReadOnlyField()
    days_until_due = serializers.ReadOnlyField()
    
    # Related evidence
    evidence_count = serializers.SerializerMethodField()
    primary_evidence = serializers.SerializerMethodField()
    
    class Meta:
        model = ControlAssessment
        fields = [
            'id', 'assessment_id', 'control', 'control_details', 'applicability',
            'applicability_rationale', 'status', 'implementation_status',
            'assigned_to', 'assigned_to_name', 'reviewer', 'reviewer_name',
            'due_date', 'started_date', 'completed_date', 'current_state_description',
            'target_state_description', 'gap_analysis', 'implementation_approach',
            'maturity_level', 'risk_rating', 'compliance_score', 'assessment_notes',
            'reviewer_comments', 'remediation_plan', 'remediation_due_date',
            'remediation_owner', 'remediation_owner_name', 'version', 'change_log',
            'is_overdue', 'is_complete', 'completion_percentage', 'days_until_due',
            'evidence_count', 'primary_evidence', 'created_by_username',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'assessment_id', 'started_date', 'completed_date', 'version',
            'change_log', 'created_at', 'updated_at'
        ]
    
    def get_evidence_count(self, obj):
        return obj.evidence_links.count()
    
    def get_primary_evidence(self, obj):
        primary_evidence = obj.evidence_links.filter(is_primary_evidence=True)
        if primary_evidence.exists():
            return ControlEvidenceSerializer(primary_evidence.first().evidence).data
        return None


class ControlAssessmentCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating assessments."""
    
    class Meta:
        model = ControlAssessment
        fields = [
            'control', 'applicability', 'applicability_rationale', 'status',
            'implementation_status', 'assigned_to', 'reviewer', 'due_date',
            'current_state_description', 'target_state_description', 'gap_analysis',
            'implementation_approach', 'maturity_level', 'risk_rating',
            'compliance_score', 'assessment_notes', 'reviewer_comments',
            'remediation_plan', 'remediation_due_date', 'remediation_owner'
        ]
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Track significant changes for change log
        significant_fields = [
            'applicability', 'status', 'implementation_status', 'assigned_to',
            'due_date', 'risk_rating', 'compliance_score'
        ]
        
        changes = []
        for field in significant_fields:
            if field in validated_data and getattr(instance, field) != validated_data[field]:
                old_value = getattr(instance, field)
                new_value = validated_data[field]
                changes.append(f'{field}: "{old_value}" → "{new_value}"')
        
        # Update the instance
        updated_instance = super().update(instance, validated_data)
        
        # Log changes if any
        if changes:
            user = self.context['request'].user
            change_description = f'Assessment updated: {", ".join(changes)}'
            updated_instance.add_change_log_entry(user, change_description)
        
        return updated_instance


class AssessmentStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating assessment status with notes."""
    status = serializers.ChoiceField(choices=ControlAssessment.STATUS_CHOICES)
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    
    def update_assessment_status(self, assessment):
        """Update assessment status with logging."""
        new_status = self.validated_data['status']
        notes = self.validated_data.get('notes', '')
        user = self.context['request'].user
        
        assessment.update_status(new_status, user, notes)
        return assessment


class BulkAssessmentCreateSerializer(serializers.Serializer):
    """Serializer for creating assessments in bulk for a framework."""
    framework_id = serializers.IntegerField()
    default_due_date = serializers.DateField(required=False)
    default_assigned_to = serializers.IntegerField(required=False)
    default_applicability = serializers.ChoiceField(
        choices=ControlAssessment.APPLICABILITY_CHOICES,
        default='to_be_determined'
    )
    controls = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="Specific control IDs to create assessments for. If empty, creates for all framework controls."
    )
    
    def validate_framework_id(self, value):
        try:
            Framework.objects.get(id=value)
        except Framework.DoesNotExist:
            raise serializers.ValidationError("Framework not found")
        return value
    
    def validate_default_assigned_to(self, value):
        if value:
            try:
                User.objects.get(id=value)
            except User.DoesNotExist:
                raise serializers.ValidationError("User not found")
        return value
    
    def create_bulk_assessments(self):
        """Create assessments in bulk."""
        framework = Framework.objects.get(id=self.validated_data['framework_id'])
        user = self.context['request'].user
        
        # Get controls to create assessments for
        if self.validated_data.get('controls'):
            controls = Control.objects.filter(
                id__in=self.validated_data['controls'],
                clauses__framework=framework
            ).distinct()
        else:
            controls = Control.objects.filter(clauses__framework=framework).distinct()
        
        created_assessments = []
        defaults = {
            'created_by': user,
            'applicability': self.validated_data['default_applicability']
        }
        
        if self.validated_data.get('default_due_date'):
            defaults['due_date'] = self.validated_data['default_due_date']
        
        if self.validated_data.get('default_assigned_to'):
            defaults['assigned_to_id'] = self.validated_data['default_assigned_to']
        
        for control in controls:
            # Check if assessment already exists
            existing = ControlAssessment.objects.filter(control=control).first()
            if not existing:
                assessment = ControlAssessment.objects.create(
                    control=control,
                    **defaults
                )
                created_assessments.append(assessment)
        
        return created_assessments


class AssessmentEvidenceSerializer(serializers.ModelSerializer):
    """Serializer for assessment evidence links."""
    evidence_details = ControlEvidenceSerializer(source='evidence', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = AssessmentEvidence
        fields = [
            'id', 'assessment', 'evidence', 'evidence_details', 'evidence_purpose',
            'is_primary_evidence', 'created_by_username', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class AssessmentProgressSerializer(serializers.Serializer):
    """Serializer for assessment progress reporting."""
    framework_id = serializers.IntegerField(required=False)
    total_assessments = serializers.IntegerField()
    completed_assessments = serializers.IntegerField()
    overdue_assessments = serializers.IntegerField()
    completion_percentage = serializers.FloatField()
    
    status_breakdown = serializers.DictField()
    applicability_breakdown = serializers.DictField()
    risk_breakdown = serializers.DictField()
    
    upcoming_due_dates = serializers.ListField()
    assignments_by_user = serializers.DictField()