from celery import shared_task
from django.utils import timezone
import logging

from .models import AssessmentReport
from .services import AssessmentReportGenerator

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def generate_assessment_report_task(self, report_id):
    """
    Celery task to generate assessment reports asynchronously.
    
    Args:
        report_id (int): ID of the AssessmentReport to generate
        
    Returns:
        dict: Generation result with status and details
    """
    try:
        report = AssessmentReport.objects.get(id=report_id)
        logger.info(f"Starting report generation for report {report_id}")
        
        # Update status to processing if not already set
        if report.status == 'pending':
            report.status = 'processing'
            report.generation_started_at = timezone.now()
            report.save()
        
        # Generate the report
        generator = AssessmentReportGenerator(report)
        document = generator.generate_report()
        
        logger.info(f"Report {report_id} generated successfully: {document.file.name}")
        
        return {
            'status': 'success',
            'report_id': report_id,
            'document_id': document.id,
            'filename': document.file.name,
            'message': 'Report generated successfully'
        }
        
    except AssessmentReport.DoesNotExist:
        logger.error(f"Report {report_id} not found")
        return {
            'status': 'error',
            'report_id': report_id,
            'message': f'Report {report_id} not found'
        }
        
    except Exception as e:
        logger.error(f"Error generating report {report_id}: {str(e)}")
        
        # Update report status on failure
        try:
            report = AssessmentReport.objects.get(id=report_id)
            report.status = 'failed'
            report.error_message = str(e)
            report.generation_completed_at = timezone.now()
            report.save()
        except AssessmentReport.DoesNotExist:
            pass
        
        # Retry the task if retries are available
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying report generation for {report_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=e)
        
        return {
            'status': 'error',
            'report_id': report_id,
            'message': f'Report generation failed after {self.max_retries + 1} attempts: {str(e)}'
        }


@shared_task
def cleanup_old_reports(days_old=30):
    """
    Clean up old generated reports to save storage space.
    
    Args:
        days_old (int): Delete reports older than this many days
        
    Returns:
        dict: Cleanup results
    """
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=days_old)
    
    # Find old reports
    old_reports = AssessmentReport.objects.filter(
        requested_at__lt=cutoff_date,
        status='completed'
    ).select_related('generated_file')
    
    deleted_count = 0
    storage_saved = 0
    
    for report in old_reports:
        try:
            if report.generated_file:
                # Track storage saved
                if report.generated_file.file_size:
                    storage_saved += report.generated_file.file_size
                
                # Delete the file and document
                report.generated_file.delete()
            
            # Delete the report record
            report.delete()
            deleted_count += 1
            
        except Exception as e:
            logger.error(f"Error deleting old report {report.id}: {str(e)}")
    
    logger.info(f"Cleaned up {deleted_count} old reports, saved {storage_saved} bytes of storage")
    
    return {
        'status': 'success',
        'deleted_count': deleted_count,
        'storage_saved_bytes': storage_saved,
        'message': f'Cleaned up {deleted_count} reports older than {days_old} days'
    }


@shared_task
def generate_scheduled_reports():
    """
    Generate any scheduled reports (future enhancement).
    This is a placeholder for future scheduled reporting functionality.
    """
    # Future implementation could include:
    # - Weekly compliance summaries
    # - Monthly gap analysis reports
    # - Quarterly compliance dashboards
    # - Custom scheduled reports per tenant
    
    logger.info("Scheduled report generation not yet implemented")
    return {
        'status': 'success',
        'message': 'Scheduled report generation placeholder executed'
    }