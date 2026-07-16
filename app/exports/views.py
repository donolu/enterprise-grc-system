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
from .models import TenantDataExport
from .audit import (
    assessment_report_display,
    audit_export_change,
    export_changed_values,
    snapshot_assessment_report,
    snapshot_tenant_data_export,
    tenant_data_export_display,
)
from .serializers import (
    AssessmentReportSerializer, 
    AssessmentReportCreateSerializer,
    ReportGenerationStatusSerializer,
    TenantDataExportSerializer,
    TenantDataExportCreateSerializer,
    TenantDataExportStatusSerializer,
)
from .services import AssessmentReportGenerator, get_export_coverage_manifest
from .tasks import generate_assessment_report_task, generate_tenant_data_export_task


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
    throttle_scope = "exports"
    
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
        report = serializer.save(requested_by=self.request.user)
        audit_export_change(
            event='ASSESSMENT_REPORT_REQUESTED',
            actor=self.request.user,
            target=report,
            object_display=assessment_report_display(report),
            request=self.request,
            new=snapshot_assessment_report(report),
        )

    def perform_update(self, serializer):
        previous = snapshot_assessment_report(serializer.instance)
        report = serializer.save()
        new = snapshot_assessment_report(report)
        previous_changed, new_changed = export_changed_values(previous, new)
        if previous_changed or new_changed:
            audit_export_change(
                event='ASSESSMENT_REPORT_UPDATED',
                actor=self.request.user,
                target=report,
                object_display=assessment_report_display(report),
                request=self.request,
                previous=previous_changed,
                new=new_changed,
            )

    def perform_destroy(self, instance):
        previous = snapshot_assessment_report(instance)
        audit_export_change(
            event='ASSESSMENT_REPORT_DELETED',
            actor=self.request.user,
            target=instance,
            object_display=assessment_report_display(instance),
            request=self.request,
            previous=previous,
        )
        instance.delete()
    
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
            previous = snapshot_assessment_report(report)
            report.status = 'processing'
            report.generation_started_at = timezone.now()
            report.save()
            new = snapshot_assessment_report(report)
            previous_changed, new_changed = export_changed_values(previous, new)
            audit_export_change(
                event='ASSESSMENT_REPORT_GENERATION_STARTED',
                actor=request.user,
                target=report,
                object_display=assessment_report_display(report),
                request=request,
                previous=previous_changed,
                new=new_changed,
                source={'type': 'api', 'reference': 'assessment_report.generate'},
            )
            
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
                f'/api/documents/{report.generated_file.id}/download/'
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
        audit_export_change(
            event='ASSESSMENT_REPORT_DOWNLOAD_REQUESTED',
            actor=request.user,
            target=report,
            object_display=assessment_report_display(report),
            request=request,
            new={
                'generated_file_id': report.generated_file_id,
                'filename': report.generated_file.file_name,
                'file_size': report.generated_file.file_size,
            },
            source={'type': 'api', 'reference': 'assessment_report.download'},
        )
        return Response({
            'download_url': request.build_absolute_uri(
                f'/api/documents/{report.generated_file.id}/download/'
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
            audit_export_change(
                event='ASSESSMENT_REPORT_REQUESTED',
                actor=request.user,
                target=report,
                object_display=assessment_report_display(report),
                request=request,
                new=snapshot_assessment_report(report),
                source={'type': 'api', 'reference': 'assessment_report.quick_generate'},
            )
            
            try:
                # Start async generation
                generate_assessment_report_task.delay(report.id)
                
                # Update status
                previous = snapshot_assessment_report(report)
                report.status = 'processing'
                report.generation_started_at = timezone.now()
                report.save()
                new = snapshot_assessment_report(report)
                previous_changed, new_changed = export_changed_values(previous, new)
                audit_export_change(
                    event='ASSESSMENT_REPORT_GENERATION_STARTED',
                    actor=request.user,
                    target=report,
                    object_display=assessment_report_display(report),
                    request=request,
                    previous=previous_changed,
                    new=new_changed,
                    source={'type': 'api', 'reference': 'assessment_report.quick_generate'},
                )
                
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
            'control'
        ).prefetch_related('control__clauses__framework')
        
        if framework_id:
            assessments = assessments.filter(control__clauses__framework_id=framework_id)
        
        if search:
            assessments = assessments.filter(
                Q(control__control_id__icontains=search) |
                Q(control__name__icontains=search)
            )
        
        # Limit results to prevent large responses
        assessments = assessments.distinct()[:100]
        
        assessment_data = [
            {
                'id': assessment.id,
                'control_id': assessment.control.control_id,
                'control_title': assessment.control.name,
                'status': assessment.status,
                'framework_name': ', '.join(
                    sorted({
                        clause.framework.short_name
                        for clause in assessment.control.clauses.all()
                    })
                )
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


@extend_schema_view(
    list=extend_schema(
        summary="List tenant data exports",
        description="Retrieve tenant data export jobs requested by the current user.",
        tags=['Data Exports'],
    ),
    create=extend_schema(
        summary="Create tenant data export",
        description="Create a tenant-wide GRC data export and start asynchronous generation.",
        tags=['Data Exports'],
    ),
    retrieve=extend_schema(
        summary="Get tenant data export",
        description="Retrieve status and download metadata for a tenant data export.",
        tags=['Data Exports'],
    ),
    destroy=extend_schema(
        summary="Delete tenant data export",
        description="Delete a tenant data export job and its generated document reference.",
        tags=['Data Exports'],
    ),
)
class TenantDataExportViewSet(viewsets.ModelViewSet):
    """
    Tenant-scoped customer data exports across all GRC modules.
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['export_format', 'status']
    throttle_scope = 'exports'
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        return TenantDataExport.objects.filter(
            requested_by=self.request.user
        ).select_related('requested_by', 'generated_file')

    def get_serializer_class(self):
        if self.action == 'create':
            return TenantDataExportCreateSerializer
        return TenantDataExportSerializer

    def perform_create(self, serializer):
        data_export = serializer.save(requested_by=self.request.user)
        audit_export_change(
            event='TENANT_DATA_EXPORT_REQUESTED',
            actor=self.request.user,
            target=data_export,
            object_display=tenant_data_export_display(data_export),
            request=self.request,
            new=snapshot_tenant_data_export(data_export),
        )
        previous = snapshot_tenant_data_export(data_export)
        data_export.status = 'processing'
        data_export.generation_started_at = timezone.now()
        data_export.save(update_fields=['status', 'generation_started_at'])
        new = snapshot_tenant_data_export(data_export)
        previous_changed, new_changed = export_changed_values(previous, new)
        audit_export_change(
            event='TENANT_DATA_EXPORT_GENERATION_STARTED',
            actor=self.request.user,
            target=data_export,
            object_display=tenant_data_export_display(data_export),
            request=self.request,
            previous=previous_changed,
            new=new_changed,
            source={'type': 'api', 'reference': 'tenant_data_export.create'},
        )
        generate_tenant_data_export_task.delay(data_export.id)

    def perform_destroy(self, instance):
        previous = snapshot_tenant_data_export(instance)
        audit_export_change(
            event='TENANT_DATA_EXPORT_DELETED',
            actor=self.request.user,
            target=instance,
            object_display=tenant_data_export_display(instance),
            request=self.request,
            previous=previous,
        )
        instance.delete()

    @extend_schema(
        summary="Get export coverage manifest",
        description="Return documented module coverage and supported formats for tenant data exports.",
        tags=['Data Exports'],
    )
    @action(detail=False, methods=['get'])
    def coverage(self, request):
        return Response({'modules': get_export_coverage_manifest()})

    @extend_schema(
        summary="Regenerate tenant data export",
        description="Start asynchronous generation for a failed or pending tenant data export.",
        responses={
            202: OpenApiResponse(description='Export generation started'),
            400: OpenApiResponse(description='Export already processing or completed'),
        },
        tags=['Data Exports'],
    )
    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        data_export = self.get_object()

        if data_export.status == 'processing':
            return Response(
                {'error': 'Export is already being generated'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if data_export.status == 'completed':
            return Response(
                {'message': 'Export is already completed'},
                status=status.HTTP_200_OK,
            )

        previous = snapshot_tenant_data_export(data_export)
        generate_tenant_data_export_task.delay(data_export.id)
        data_export.status = 'processing'
        data_export.generation_started_at = timezone.now()
        data_export.error_message = ''
        data_export.save(update_fields=['status', 'generation_started_at', 'error_message'])
        new = snapshot_tenant_data_export(data_export)
        previous_changed, new_changed = export_changed_values(previous, new)
        audit_export_change(
            event='TENANT_DATA_EXPORT_GENERATION_STARTED',
            actor=request.user,
            target=data_export,
            object_display=tenant_data_export_display(data_export),
            request=request,
            previous=previous_changed,
            new=new_changed,
            source={'type': 'api', 'reference': 'tenant_data_export.generate'},
        )
        return Response(
            {
                'message': 'Export generation started',
                'export_id': data_export.id,
                'status': data_export.status,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=['get'])
    def status_check(self, request, pk=None):
        data_export = self.get_object()
        serializer = TenantDataExportSerializer(data_export, context={'request': request})
        response_data = {
            'export_id': data_export.id,
            'status': data_export.status,
            'message': self._get_export_status_message(data_export),
            'download_url': serializer.data.get('download_url'),
            'record_counts': data_export.record_counts,
        }
        if data_export.status == 'failed':
            response_data['error_details'] = data_export.error_message

        return Response(TenantDataExportStatusSerializer(response_data).data)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        data_export = self.get_object()
        if data_export.status != 'completed' or not data_export.generated_file:
            return Response(
                {'error': 'Export is not ready for download'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TenantDataExportSerializer(data_export, context={'request': request})
        audit_export_change(
            event='TENANT_DATA_EXPORT_DOWNLOAD_REQUESTED',
            actor=request.user,
            target=data_export,
            object_display=tenant_data_export_display(data_export),
            request=request,
            new={
                'generated_file_id': data_export.generated_file_id,
                'filename': data_export.generated_file.file_name,
                'file_size': data_export.generated_file.file_size,
                'record_counts': data_export.record_counts,
            },
            source={'type': 'api', 'reference': 'tenant_data_export.download'},
        )
        return Response({
            'download_url': serializer.data['download_url'],
            'document_id': data_export.generated_file_id,
            'filename': data_export.generated_file.file_name,
            'size': data_export.generated_file.file_size,
        })

    def _get_export_status_message(self, data_export):
        if data_export.status == 'pending':
            return 'Export is queued for generation'
        if data_export.status == 'processing':
            return 'Export is being generated'
        if data_export.status == 'completed':
            return 'Export has been generated successfully'
        if data_export.status == 'failed':
            return f'Export generation failed: {data_export.error_message}'
        return 'Unknown status'
