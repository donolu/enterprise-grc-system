from rest_framework import serializers
from catalogs.models import Framework, ControlAssessment
from core.serializers import DocumentSerializer
from .models import AssessmentReport


class AssessmentReportSerializer(serializers.ModelSerializer):
    """Serializer for AssessmentReport model."""
    
    framework_name = serializers.CharField(source='framework.name', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    generated_file_details = DocumentSerializer(source='generated_file', read_only=True)
    
    class Meta:
        model = AssessmentReport
        fields = [
            'id',
            'report_type',
            'title', 
            'description',
            'framework',
            'framework_name',
            'requested_by',
            'requested_by_name',
            'requested_at',
            'status',
            'generated_file',
            'generated_file_details',
            'generation_started_at',
            'generation_completed_at',
            'error_message',
            'include_evidence_summary',
            'include_implementation_notes', 
            'include_overdue_items',
            'include_charts',
        ]
        read_only_fields = [
            'id',
            'requested_by',
            'requested_at',
            'status',
            'generated_file',
            'generation_started_at',
            'generation_completed_at',
            'error_message',
        ]
    
    def validate(self, data):
        """Validate report configuration."""
        report_type = data.get('report_type')
        framework = data.get('framework')
        
        # Some report types require a framework
        if report_type == 'compliance_gap' and not framework:
            raise serializers.ValidationError({
                'framework': 'Framework is required for compliance gap analysis.'
            })
        
        return data


class AssessmentReportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating assessment reports."""
    
    assessment_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="List of assessment IDs to include in the report"
    )
    
    class Meta:
        model = AssessmentReport
        fields = [
            'report_type',
            'title',
            'description', 
            'framework',
            'assessment_ids',
            'include_evidence_summary',
            'include_implementation_notes',
            'include_overdue_items', 
            'include_charts',
        ]
    
    def validate_assessment_ids(self, value):
        """Validate that assessment IDs exist and are accessible."""
        if value:
            # Check that all assessments exist and are accessible to the user
            request = self.context.get('request')
            if request and hasattr(request, 'user'):
                # In a multi-tenant system, assessments are automatically scoped
                existing_ids = set(
                    ControlAssessment.objects.filter(id__in=value).values_list('id', flat=True)
                )
                invalid_ids = set(value) - existing_ids
                if invalid_ids:
                    raise serializers.ValidationError(
                        f"Invalid assessment IDs: {list(invalid_ids)}"
                    )
        return value
    
    def create(self, validated_data):
        """Create assessment report with specific assessments."""
        assessment_ids = validated_data.pop('assessment_ids', [])
        
        # Set requested_by from context
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['requested_by'] = request.user
        
        # Create the report
        report = super().create(validated_data)
        
        # Add specific assessments if provided
        if assessment_ids:
            assessments = ControlAssessment.objects.filter(id__in=assessment_ids)
            report.assessments.set(assessments)
        
        return report


class ReportGenerationStatusSerializer(serializers.Serializer):
    """Serializer for report generation status responses."""
    
    report_id = serializers.IntegerField()
    status = serializers.CharField()
    message = serializers.CharField()
    download_url = serializers.URLField(required=False)
    error_details = serializers.CharField(required=False)