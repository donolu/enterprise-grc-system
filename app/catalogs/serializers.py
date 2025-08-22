from rest_framework import serializers
from .models import Framework, Clause, Control, ControlEvidence, FrameworkMapping
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