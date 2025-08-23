from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from catalogs.models import Framework, ControlAssessment
from .models import AssessmentReport
from .serializers import (
    AssessmentReportSerializer, 
    AssessmentReportCreateSerializer,
    ReportGenerationStatusSerializer
)
from .services import AssessmentReportGenerator
from .tasks import generate_assessment_report_task


@extend_schema_view(
    list=extend_schema(
        summary="List assessment reports",
        description="Retrieve a list of assessment reports created by the current user with filtering capabilities.",
        parameters=[
            OpenApiParameter(
                name='report_type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by report type (summary, detailed, compliance, etc.)'
            ),
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by report status (pending, processing, completed, failed)'
            ),
            OpenApiParameter(
                name='framework',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by framework ID'
            ),
        ],
        tags=['Reports'],
    ),
    create=extend_schema(
        summary="Create assessment report",
        description="Create a new assessment report configuration. Use the 'generate' action to start report generation.",
        tags=['Reports'],
    ),
    retrieve=extend_schema(
        summary="Get report details",
        description="Retrieve detailed information about a specific assessment report including generation status.",
        tags=['Reports'],
    ),
    update=extend_schema(
        summary="Update report",
        description="Update an existing assessment report configuration. Cannot update reports that are processing or completed.",
        tags=['Reports'],
    ),
    destroy=extend_schema(
        summary="Delete report",
        description="Delete an assessment report and its generated file if it exists.",
        tags=['Reports'],
    ),
)
class AssessmentReportViewSet(viewsets.ModelViewSet):
    """
    **Assessment Report Management**
    
    This ViewSet provides comprehensive management of assessment reports including:
    - Report configuration and creation
    - Asynchronous report generation with status tracking
    - Download management for completed reports
    - Framework and assessment selection options
    
    **Key Features:**
    - Support for multiple report types (summary, detailed, compliance)
    - Async PDF generation with progress tracking
    - Framework-specific and assessment-specific reporting
    - Professional PDF output with charts and analytics
    - Secure file storage and download links
    
    **Report Generation Workflow:**
    1. Create report configuration
    2. Trigger generation (async)
    3. Monitor generation status
    4. Download completed report
    
    **Common Use Cases:**
    - Generate compliance reports for audits
    - Create assessment summaries for management
    - Export detailed findings for remediation
    - Produce framework-specific reports
    """
    
    serializer_class = AssessmentReportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['report_type', 'status', 'framework']
    
    def get_queryset(self):
        """Return reports for the current user's tenant."""
        return AssessmentReport.objects.filter(
            requested_by=self.request.user
        ).select_related('framework', 'requested_by', 'generated_file')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return AssessmentReportCreateSerializer
        return AssessmentReportSerializer
    
    def perform_create(self, serializer):
        """Create report and trigger generation."""
        serializer.save(requested_by=self.request.user)
    
    @extend_schema(
        summary="Generate report",
        description="Start asynchronous generation of the assessment report. Returns immediately with status tracking information.",
        responses={
            202: OpenApiResponse(
                description='Report generation started',
                examples=[
                    OpenApiExample(
                        'Generation Started',
                        summary='Report generation initiated',
                        value={
                            'message': 'Report generation started',
                            'report_id': 123,
                            'status': 'processing'
                        }
                    ),
                ]
            ),
            400: OpenApiResponse(description='Report already processing or completed'),
            500: OpenApiResponse(description='Failed to start generation'),
        },
        tags=['Reports'],
    )
    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """Start asynchronous generation of the assessment report."""
        report = self.get_object()
        
        if report.status in ['processing']:
            return Response(
                {'error': 'Report is already being generated'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if report.status == 'completed':
            return Response(
                {'message': 'Report is already completed'},
                status=status.HTTP_200_OK
            )
        
        try:
            # Start async generation
            generate_assessment_report_task.delay(report.id)
            
            # Update status
            report.status = 'processing'
            report.generation_started_at = timezone.now()
            report.save()
            
            return Response({
                'message': 'Report generation started',
                'report_id': report.id,
                'status': report.status
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to start report generation: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def status_check(self, request, pk=None):
        """Check report generation status."""
        report = self.get_object()
        
        response_data = {
            'report_id': report.id,
            'status': report.status,
            'message': self._get_status_message(report)
        }
        
        if report.status == 'completed' and report.generated_file:
            response_data['download_url'] = request.build_absolute_uri(
                f'/api/core/documents/{report.generated_file.id}/download/'
            )
        elif report.status == 'failed':
            response_data['error_details'] = report.error_message
        
        serializer = ReportGenerationStatusSerializer(response_data)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download the generated report."""
        report = self.get_object()
        
        if report.status != 'completed' or not report.generated_file:
            return Response(
                {'error': 'Report is not ready for download'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Redirect to document download endpoint
        return Response({
            'download_url': request.build_absolute_uri(
                f'/api/core/documents/{report.generated_file.id}/download/'
            )
        })
    
    @extend_schema(
        summary="Quick generate report",
        description="Create a new assessment report and immediately start generation in a single operation.",
        request=AssessmentReportCreateSerializer,
        responses={
            201: OpenApiResponse(
                description='Report created and generation started',
                examples=[
                    OpenApiExample(
                        'Quick Generation Started',
                        summary='Report created and generation initiated',
                        value={
                            'message': 'Report created and generation started',
                            'report_id': 123,
                            'status': 'processing'
                        }
                    ),
                ]
            ),
            400: OpenApiResponse(description='Invalid report configuration'),
            500: OpenApiResponse(description='Failed to start generation'),
        },
        tags=['Reports'],
    )
    @action(detail=False, methods=['post'])
    def quick_generate(self, request):
        """Create a new assessment report and immediately start generation."""
        serializer = AssessmentReportCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            report = serializer.save(requested_by=request.user)
            
            try:
                # Start async generation
                generate_assessment_report_task.delay(report.id)
                
                # Update status
                report.status = 'processing'
                report.generation_started_at = timezone.now()
                report.save()
                
                return Response({
                    'message': 'Report created and generation started',
                    'report_id': report.id,
                    'status': report.status
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                # Clean up created report on failure
                report.delete()
                return Response(
                    {'error': f'Failed to start report generation: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def framework_options(self, request):
        """Get available frameworks for report generation."""
        frameworks = Framework.objects.filter(
            status='active'
        ).values('id', 'name', 'short_name', 'description')
        
        return Response({'frameworks': list(frameworks)})
    
    @action(detail=False, methods=['get'])
    def assessment_options(self, request):
        """Get available assessments for report generation."""
        framework_id = request.query_params.get('framework_id')
        search = request.query_params.get('search', '')
        
        assessments = ControlAssessment.objects.select_related(
            'control', 'control__clause'
        )
        
        if framework_id:
            assessments = assessments.filter(control__clause__framework_id=framework_id)
        
        if search:
            assessments = assessments.filter(
                Q(control__control_id__icontains=search) |
                Q(control__title__icontains=search)
            )
        
        # Limit results to prevent large responses
        assessments = assessments[:100]
        
        assessment_data = [
            {
                'id': assessment.id,
                'control_id': assessment.control.control_id,
                'control_title': assessment.control.title,
                'status': assessment.status,
                'framework_name': assessment.control.clause.framework.short_name
            }
            for assessment in assessments
        ]
        
        return Response({'assessments': assessment_data})
    
    def _get_status_message(self, report):
        """Get user-friendly status message."""
        if report.status == 'pending':
            return 'Report is queued for generation'
        elif report.status == 'processing':
            return 'Report is being generated'
        elif report.status == 'completed':
            return 'Report has been generated successfully'
        elif report.status == 'failed':
            return f'Report generation failed: {report.error_message}'
        else:
            return 'Unknown status'