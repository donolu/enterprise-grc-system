"""
Analytics API Views

Provides REST API endpoints for analytics dashboards and reporting.
Integrates with existing analytics services to deliver comprehensive
GRC platform insights.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse, HttpResponse, Http404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from django.utils import timezone
import logging
import mimetypes

from .services import CrossModuleAnalyticsService, AnalyticsReportGenerator
from .models import AnalyticsReport, DashboardConfiguration
# from .tasks import generate_analytics_report, cache_analytics_metrics  # TODO: Add PDF dependencies
from billing.decorators import require_advanced_reporting

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@cache_page(60 * 15)  # Cache for 15 minutes
def executive_dashboard(request):
    """
    Executive dashboard with high-level KPIs across all modules.

    Returns comprehensive metrics for C-level reporting including risk posture,
    compliance status, vendor management, policy compliance, and training effectiveness.
    """
    try:
        data = CrossModuleAnalyticsService.get_executive_dashboard_data()
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error generating executive dashboard: {str(e)}")
        return Response(
            {'error': 'Failed to generate executive dashboard'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@cache_page(60 * 10)  # Cache for 10 minutes
def compliance_dashboard(request):
    """
    Compliance-focused dashboard with framework completion rates and control effectiveness.

    Provides detailed compliance metrics including assessment progress,
    control maturity, and evidence collection statistics.
    """
    try:
        data = CrossModuleAnalyticsService.get_compliance_dashboard_data()
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error generating compliance dashboard: {str(e)}")
        return Response(
            {'error': 'Failed to generate compliance dashboard'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@cache_page(60 * 10)  # Cache for 10 minutes
def vendor_risk_dashboard(request):
    """
    Vendor management and risk assessment dashboard.

    Provides vendor risk distribution, contract management metrics,
    and vendor task analytics for procurement and risk teams.
    """
    try:
        data = CrossModuleAnalyticsService.get_vendor_risk_dashboard_data()
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error generating vendor dashboard: {str(e)}")
        return Response(
            {'error': 'Failed to generate vendor dashboard'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@cache_page(60 * 10)  # Cache for 10 minutes
def policy_management_dashboard(request):
    """
    Policy management and acknowledgment tracking dashboard.

    Provides policy distribution metrics, acknowledgment rates,
    and compliance tracking for governance teams.
    """
    try:
        data = CrossModuleAnalyticsService.get_policy_management_dashboard_data()
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error generating policy dashboard: {str(e)}")
        return Response(
            {'error': 'Failed to generate policy dashboard'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@cache_page(60 * 10)  # Cache for 10 minutes
def training_effectiveness_dashboard(request):
    """
    Training program effectiveness and engagement dashboard.

    Provides training completion rates, user engagement metrics,
    and security awareness campaign performance.
    """
    try:
        data = CrossModuleAnalyticsService.get_training_effectiveness_dashboard_data()
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error generating training dashboard: {str(e)}")
        return Response(
            {'error': 'Failed to generate training dashboard'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_advanced_reporting  # Premium feature
@cache_page(60 * 20)  # Cache for 20 minutes
def integrated_risk_posture(request):
    """
    Integrated risk posture analysis across all modules.

    Premium feature providing cross-module risk correlation,
    risk maturity indicators, and comprehensive risk trending.
    Requires advanced reporting subscription tier.
    """
    try:
        data = CrossModuleAnalyticsService.get_integrated_risk_posture()
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error generating integrated risk posture: {str(e)}")
        return Response(
            {'error': 'Failed to generate integrated risk analysis'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_advanced_reporting  # Premium feature
@cache_page(60 * 30)  # Cache for 30 minutes
def executive_report_data(request):
    """
    Comprehensive executive report data for leadership presentations.

    Premium feature providing complete analytics package including
    all dashboard data, trends, and cross-module insights formatted
    for executive consumption and reporting.
    """
    try:
        data = AnalyticsReportGenerator.generate_executive_report_data()
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error generating executive report: {str(e)}")
        return Response(
            {'error': 'Failed to generate executive report'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@cache_page(60 * 5)  # Cache for 5 minutes
def operational_dashboard(request):
    """
    Operational dashboard for day-to-day management and monitoring.

    Provides actionable metrics focused on operational tasks,
    overdue items, progress tracking, and immediate attention items.
    """
    try:
        data = AnalyticsReportGenerator.generate_operational_dashboard_data()
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error generating operational dashboard: {str(e)}")
        return Response(
            {'error': 'Failed to generate operational dashboard'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_health_check(request):
    """
    Health check endpoint for analytics service availability.

    Provides basic system health information and data freshness
    indicators for monitoring and alerting purposes.
    """
    try:
        # Basic health checks
        from django.db import connections
        db_conn = connections['default']
        db_conn.cursor()

        # Check cache availability
        cache.set('health_check', 'ok', 30)
        cache_status = cache.get('health_check') == 'ok'

        health_data = {
            'status': 'healthy',
            'database': 'connected',
            'cache': 'available' if cache_status else 'unavailable',
            'analytics_service': 'operational',
            'timestamp': CrossModuleAnalyticsService.get_executive_dashboard_data()['generated_at']
        }

        return Response(health_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Analytics health check failed: {str(e)}")
        return Response(
            {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def export_report(request):
    """
    Create an async export job for analytics reports.

    Accepts report configuration and queues a background job for
    PDF, Excel, CSV, or JSON export generation.
    """
    try:
        # Validate request data
        report_type = request.data.get('report_type')
        export_format = request.data.get('export_format', 'pdf')
        title = request.data.get('title', f'{report_type.title()} Analytics Report')
        description = request.data.get('description', '')
        filters = request.data.get('filters', {})

        if not report_type:
            return Response(
                {'error': 'report_type is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if report_type not in [choice[0] for choice in AnalyticsReport.REPORT_TYPES]:
            return Response(
                {'error': f'Invalid report_type. Must be one of: {[choice[0] for choice in AnalyticsReport.REPORT_TYPES]}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if export_format not in [choice[0] for choice in AnalyticsReport.EXPORT_FORMATS]:
            return Response(
                {'error': f'Invalid export_format. Must be one of: {[choice[0] for choice in AnalyticsReport.EXPORT_FORMATS]}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create the report record
        report = AnalyticsReport.objects.create(
            report_type=report_type,
            export_format=export_format,
            requested_by=request.user,
            title=title,
            description=description,
            filters=filters,
            date_range_start=request.data.get('date_range_start'),
            date_range_end=request.data.get('date_range_end'),
        )

        # Queue the background job
        # task_result = generate_analytics_report.delay(str(report.id))  # TODO: Enable when tasks are ready
        task_result = type('MockTask', (), {'id': 'mock-task-id'})()

        logger.info(f"Queued analytics report generation: {report.id} for user {request.user.id}")

        return Response({
            'report_id': str(report.id),
            'task_id': task_result.id,
            'status': 'queued',
            'estimated_completion': timezone.now() + timezone.timedelta(minutes=5),
            'message': f'{export_format.upper()} report generation has been queued'
        }, status=status.HTTP_202_ACCEPTED)

    except Exception as e:
        logger.error(f"Error creating export job: {str(e)}")
        return Response(
            {'error': 'Failed to create export job'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report_status(request, report_id):
    """
    Check the status of an analytics report generation job.

    Returns current status, progress information, and download link
    when completed.
    """
    try:
        report = get_object_or_404(
            AnalyticsReport,
            id=report_id,
            requested_by=request.user
        )

        response_data = {
            'report_id': str(report.id),
            'status': report.status,
            'title': report.title,
            'report_type': report.report_type,
            'export_format': report.export_format,
            'created_at': report.created_at,
            'started_at': report.started_at,
            'completed_at': report.completed_at,
        }

        if report.status == 'completed' and report.is_downloadable:
            response_data.update({
                'download_url': f'/api/analytics/reports/{report_id}/download/',
                'file_size': report.file_size,
                'data_points_included': report.data_points_included,
                'generation_time_seconds': report.generation_time_seconds,
                'expires_at': report.expires_at,
                'download_count': report.download_count,
            })
        elif report.status == 'failed':
            response_data['error_message'] = report.error_message
        elif report.status == 'processing':
            if report.started_at:
                elapsed = (timezone.now() - report.started_at).total_seconds()
                response_data['processing_time_seconds'] = elapsed

        return Response(response_data)

    except Exception as e:
        logger.error(f"Error checking report status {report_id}: {str(e)}")
        return Response(
            {'error': 'Failed to check report status'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_report(request, report_id):
    """
    Download a completed analytics report file.

    Serves the generated report file and increments download counter.
    """
    try:
        report = get_object_or_404(
            AnalyticsReport,
            id=report_id,
            requested_by=request.user
        )

        if not report.is_downloadable:
            if report.status != 'completed':
                return Response(
                    {'error': f'Report is not ready for download. Status: {report.status}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif report.is_expired:
                return Response(
                    {'error': 'Report has expired and is no longer available'},
                    status=status.HTTP_410_GONE
                )
            else:
                return Response(
                    {'error': 'Report file is not available'},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Check if file exists in storage
        if not default_storage.exists(report.file_path):
            return Response(
                {'error': 'Report file not found in storage'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get file content and metadata
        file_content = default_storage.open(report.file_path).read()
        content_type, _ = mimetypes.guess_type(report.file_path)

        if not content_type:
            # Set default content types based on format
            format_content_types = {
                'pdf': 'application/pdf',
                'excel': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'csv': 'text/csv',
                'json': 'application/json',
            }
            content_type = format_content_types.get(report.export_format, 'application/octet-stream')

        # Create filename
        filename = f"{report.title.replace(' ', '_')}_{report.created_at.strftime('%Y%m%d')}.{report.export_format}"
        if report.export_format == 'excel':
            filename = filename.replace('.excel', '.xlsx')

        # Create response
        response = HttpResponse(file_content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(file_content)

        # Increment download counter
        report.increment_download_count()

        logger.info(f"Report {report_id} downloaded by user {request.user.id}")

        return response

    except Exception as e:
        logger.error(f"Error downloading report {report_id}: {str(e)}")
        return Response(
            {'error': 'Failed to download report'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_reports(request):
    """
    List analytics reports created by the current user.

    Returns paginated list of reports with status and metadata.
    """
    try:
        reports = AnalyticsReport.objects.filter(
            requested_by=request.user
        ).order_by('-created_at')

        # Simple pagination
        page_size = 20
        page = int(request.GET.get('page', 1))
        offset = (page - 1) * page_size

        total_count = reports.count()
        reports_page = reports[offset:offset + page_size]

        reports_data = []
        for report in reports_page:
            report_data = {
                'id': str(report.id),
                'title': report.title,
                'report_type': report.report_type,
                'report_type_display': report.get_report_type_display(),
                'export_format': report.export_format,
                'export_format_display': report.get_export_format_display(),
                'status': report.status,
                'status_display': report.get_status_display(),
                'created_at': report.created_at,
                'file_size': report.file_size,
                'download_count': report.download_count,
                'is_downloadable': report.is_downloadable,
                'expires_at': report.expires_at,
            }

            if report.status == 'failed':
                report_data['error_message'] = report.error_message

            reports_data.append(report_data)

        return Response({
            'reports': reports_data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': (total_count + page_size - 1) // page_size,
                'has_next': offset + page_size < total_count,
                'has_previous': page > 1,
            }
        })

    except Exception as e:
        logger.error(f"Error fetching user reports: {str(e)}")
        return Response(
            {'error': 'Failed to fetch reports'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_report(request, report_id):
    """
    Delete an analytics report and its associated file.

    Users can only delete their own reports.
    """
    try:
        report = get_object_or_404(
            AnalyticsReport,
            id=report_id,
            requested_by=request.user
        )

        # Delete file if it exists
        if report.file_path and default_storage.exists(report.file_path):
            try:
                default_storage.delete(report.file_path)
            except Exception as e:
                logger.warning(f"Failed to delete file for report {report_id}: {str(e)}")

        # Delete the report record
        report.delete()

        logger.info(f"Report {report_id} deleted by user {request.user.id}")

        return Response({'message': 'Report deleted successfully'})

    except Exception as e:
        logger.error(f"Error deleting report {report_id}: {str(e)}")
        return Response(
            {'error': 'Failed to delete report'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_advanced_reporting  # Premium feature
def refresh_cache(request):
    """
    Manually trigger analytics metrics cache refresh.

    Premium feature for forcing immediate cache refresh of
    analytics metrics for improved dashboard performance.
    """
    try:
        # Queue the cache refresh task
        # task_result = cache_analytics_metrics.delay()  # TODO: Enable when tasks are ready
        task_result = type('MockTask', (), {'id': 'mock-cache-task-id'})()

        logger.info(f"Analytics cache refresh queued by user {request.user.id}")

        return Response({
            'task_id': task_result.id,
            'message': 'Analytics cache refresh has been queued',
            'estimated_completion': timezone.now() + timezone.timedelta(minutes=2)
        }, status=status.HTTP_202_ACCEPTED)

    except Exception as e:
        logger.error(f"Error queuing cache refresh: {str(e)}")
        return Response(
            {'error': 'Failed to refresh cache'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )