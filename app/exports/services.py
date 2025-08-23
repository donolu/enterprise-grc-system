import os
import io
from datetime import datetime
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Count, Q
from django.core.files.base import ContentFile
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

from core.models import Document
from catalogs.models import ControlAssessment, Framework, AssessmentEvidence
from risk.analytics import RiskAnalyticsService, RiskReportGenerator
from risk.models import Risk, RiskAction
from .models import AssessmentReport


class AssessmentReportGenerator:
    """Service for generating assessment reports in PDF format."""
    
    def __init__(self, report: AssessmentReport):
        self.report = report
        self.font_config = FontConfiguration()
    
    def generate_report(self):
        """Generate the PDF report based on report type."""
        try:
            self.report.status = 'processing'
            self.report.generation_started_at = timezone.now()
            self.report.save()
            
            # Generate report based on type
            if self.report.report_type == 'assessment_summary':
                html_content = self._generate_assessment_summary()
            elif self.report.report_type == 'detailed_assessment':
                html_content = self._generate_detailed_assessment()
            elif self.report.report_type == 'evidence_portfolio':
                html_content = self._generate_evidence_portfolio()
            elif self.report.report_type == 'compliance_gap':
                html_content = self._generate_compliance_gap()
            elif self.report.report_type == 'risk_analytics':
                html_content = self._generate_risk_analytics_report()
            else:
                raise ValueError(f"Unknown report type: {self.report.report_type}")
            
            # Generate PDF
            pdf_content = self._render_pdf(html_content)
            
            # Save PDF as Document
            filename = self._generate_filename()
            document = self._save_pdf_document(pdf_content, filename)
            
            # Update report status
            self.report.generated_file = document
            self.report.status = 'completed'
            self.report.generation_completed_at = timezone.now()
            self.report.save()
            
            return document
            
        except Exception as e:
            self.report.status = 'failed'
            self.report.error_message = str(e)
            self.report.generation_completed_at = timezone.now()
            self.report.save()
            raise
    
    def _generate_assessment_summary(self):
        """Generate assessment summary report HTML."""
        context = {
            'report': self.report,
            'framework': self.report.framework,
            'generated_at': timezone.now(),
        }
        
        if self.report.framework:
            # Framework-specific summary
            assessments = ControlAssessment.objects.filter(
                control__clause__framework=self.report.framework
            ).select_related('control', 'assigned_to', 'control__clause')
            
            # Assessment statistics
            total_assessments = assessments.count()
            completed_assessments = assessments.filter(status='completed').count()
            in_progress_assessments = assessments.filter(status='in_progress').count()
            not_started_assessments = assessments.filter(status='not_started').count()
            overdue_assessments = assessments.filter(
                status__in=['not_started', 'in_progress'],
                due_date__lt=timezone.now().date()
            ).count()
            
            # Evidence statistics
            evidence_stats = AssessmentEvidence.objects.filter(
                assessment__in=assessments
            ).aggregate(
                total_evidence=Count('id'),
                primary_evidence=Count('id', filter=Q(is_primary_evidence=True))
            )
            
            context.update({
                'assessments': assessments,
                'total_assessments': total_assessments,
                'completed_assessments': completed_assessments,
                'in_progress_assessments': in_progress_assessments,
                'not_started_assessments': not_started_assessments,
                'overdue_assessments': overdue_assessments,
                'completion_percentage': round((completed_assessments / total_assessments * 100) if total_assessments > 0 else 0, 1),
                'evidence_stats': evidence_stats,
            })
            
            # Add risk analytics data to provide comprehensive risk context
            context.update(self._get_risk_analytics_context())
        else:
            # All assessments summary
            assessments = self.report.assessments.all()
            context['assessments'] = assessments
        
        return render_to_string('exports/reports/assessment_summary.html', context)
    
    def _generate_detailed_assessment(self):
        """Generate detailed assessment report HTML."""
        context = {
            'report': self.report,
            'generated_at': timezone.now(),
        }
        
        if self.report.framework:
            assessments = ControlAssessment.objects.filter(
                control__clause__framework=self.report.framework
            ).select_related(
                'control', 'assigned_to', 'control__clause'
            ).prefetch_related('evidence_links__evidence')
        else:
            assessments = self.report.assessments.all().select_related(
                'control', 'assigned_to', 'control__clause'
            ).prefetch_related('evidence_links__evidence')
        
        context['assessments'] = assessments
        return render_to_string('exports/reports/detailed_assessment.html', context)
    
    def _generate_evidence_portfolio(self):
        """Generate evidence portfolio report HTML."""
        context = {
            'report': self.report,
            'generated_at': timezone.now(),
        }
        
        # Get evidence across assessments
        if self.report.framework:
            evidence_links = AssessmentEvidence.objects.filter(
                assessment__control__clause__framework=self.report.framework
            ).select_related(
                'assessment', 'evidence', 'assessment__control'
            ).prefetch_related('evidence__document')
        else:
            assessment_ids = self.report.assessments.values_list('id', flat=True)
            evidence_links = AssessmentEvidence.objects.filter(
                assessment_id__in=assessment_ids
            ).select_related(
                'assessment', 'evidence', 'assessment__control'
            ).prefetch_related('evidence__document')
        
        # Group evidence by type and reuse
        evidence_summary = {}
        for link in evidence_links:
            evidence = link.evidence
            if evidence.id not in evidence_summary:
                evidence_summary[evidence.id] = {
                    'evidence': evidence,
                    'assessments': [],
                    'is_primary_count': 0,
                }
            evidence_summary[evidence.id]['assessments'].append(link.assessment)
            if link.is_primary_evidence:
                evidence_summary[evidence.id]['is_primary_count'] += 1
        
        context['evidence_summary'] = evidence_summary.values()
        return render_to_string('exports/reports/evidence_portfolio.html', context)
    
    def _generate_compliance_gap(self):
        """Generate compliance gap analysis report HTML."""
        context = {
            'report': self.report,
            'framework': self.report.framework,
            'generated_at': timezone.now(),
        }
        
        if not self.report.framework:
            raise ValueError("Compliance gap analysis requires a framework")
        
        # Get all assessments for the framework
        assessments = ControlAssessment.objects.filter(
            control__clause__framework=self.report.framework
        ).select_related('control', 'assigned_to', 'control__clause')
        
        # Categorize gaps
        not_started = assessments.filter(status='not_started')
        in_progress_overdue = assessments.filter(
            status='in_progress',
            due_date__lt=timezone.now().date()
        )
        missing_evidence = assessments.filter(
            status='completed',
            evidence_links__isnull=True
        )
        no_primary_evidence = assessments.filter(
            status='completed'
        ).exclude(
            evidence_links__is_primary_evidence=True
        )
        
        context.update({
            'not_started': not_started,
            'in_progress_overdue': in_progress_overdue,
            'missing_evidence': missing_evidence,
            'no_primary_evidence': no_primary_evidence,
            'total_gaps': (
                not_started.count() + 
                in_progress_overdue.count() + 
                missing_evidence.count() + 
                no_primary_evidence.count()
            ),
        })
        
        return render_to_string('exports/reports/compliance_gap.html', context)
    
    def _render_pdf(self, html_content):
        """Convert HTML to PDF using WeasyPrint."""
        # Define CSS for styling
        css_content = """
        @page {
            size: A4;
            margin: 2cm;
            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 10pt;
                color: #666;
            }
        }
        
        body {
            font-family: 'Helvetica', 'Arial', sans-serif;
            font-size: 11pt;
            line-height: 1.4;
            color: #333;
        }
        
        .header {
            border-bottom: 2px solid #0066cc;
            padding-bottom: 1em;
            margin-bottom: 2em;
        }
        
        .header h1 {
            color: #0066cc;
            margin: 0;
            font-size: 20pt;
        }
        
        .header .subtitle {
            color: #666;
            font-size: 12pt;
            margin-top: 0.5em;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1em;
            margin: 1em 0;
        }
        
        .stat-card {
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 1em;
            text-align: center;
        }
        
        .stat-card .number {
            font-size: 24pt;
            font-weight: bold;
            color: #0066cc;
        }
        
        .stat-card .label {
            font-size: 10pt;
            color: #666;
            margin-top: 0.5em;
        }
        
        .assessment-table {
            width: 100%;
            border-collapse: collapse;
            margin: 1em 0;
        }
        
        .assessment-table th,
        .assessment-table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
            font-size: 10pt;
        }
        
        .assessment-table th {
            background-color: #f5f5f5;
            font-weight: bold;
        }
        
        .status-badge {
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 9pt;
            font-weight: bold;
            color: white;
        }
        
        .status-completed { background-color: #28a745; }
        .status-in-progress { background-color: #ffc107; color: #333; }
        .status-not-started { background-color: #6c757d; }
        .status-overdue { background-color: #dc3545; }
        
        .page-break {
            page-break-before: always;
        }
        
        .section {
            margin: 2em 0;
        }
        
        .section h2 {
            color: #0066cc;
            border-bottom: 1px solid #0066cc;
            padding-bottom: 0.5em;
        }
        """
        
        css = CSS(string=css_content, font_config=self.font_config)
        html = HTML(string=html_content)
        
        pdf_buffer = io.BytesIO()
        html.write_pdf(pdf_buffer, stylesheets=[css], font_config=self.font_config)
        pdf_buffer.seek(0)
        
        return pdf_buffer.getvalue()
    
    def _generate_filename(self):
        """Generate appropriate filename for the report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_type = self.report.report_type.replace('_', '-')
        
        if self.report.framework:
            framework_name = self.report.framework.short_name.lower().replace(' ', '-')
            return f"{report_type}-{framework_name}-{timestamp}.pdf"
        else:
            return f"{report_type}-{timestamp}.pdf"
    
    def _save_pdf_document(self, pdf_content, filename):
        """Save PDF content as a Document."""
        document = Document(
            title=f"{self.report.title}",
            description=f"Generated assessment report: {self.report.get_report_type_display()}",
            document_type='report',
            file_category='generated',
            uploaded_by=self.report.requested_by
        )
        
        # Save the PDF content
        document.file.save(
            filename,
            ContentFile(pdf_content),
            save=False
        )
        
        # Set file metadata
        document.file_size = len(pdf_content)
        document.mime_type = 'application/pdf'
        document.save()
        
        return document
    
    def _get_risk_analytics_context(self):
        """
        Get risk analytics data to include in assessment reports.
        Provides comprehensive risk context to complement compliance data.
        """
        try:
            # Get risk overview data
            risk_overview = RiskAnalyticsService.get_risk_overview_stats()
            
            # Get risk action progress data
            action_overview = RiskAnalyticsService.get_risk_action_overview_stats()
            
            # Get executive risk summary for high-level insights
            executive_summary = RiskAnalyticsService.get_executive_risk_summary()
            
            # Get heat map data for risk visualization context
            heat_map_data = RiskAnalyticsService.get_risk_heat_map_data()
            
            # Calculate risk-compliance correlation metrics
            risk_compliance_metrics = self._calculate_risk_compliance_correlation()
            
            return {
                'risk_analytics': {
                    'overview': risk_overview,
                    'actions': action_overview,
                    'executive_summary': executive_summary,
                    'heat_map': heat_map_data,
                    'compliance_correlation': risk_compliance_metrics,
                }
            }
        except Exception as e:
            # Graceful degradation - if risk analytics fail, don't break the report
            return {
                'risk_analytics': {
                    'error': f"Risk analytics unavailable: {str(e)}",
                    'overview': {'total_risks': 0, 'active_risks': 0},
                    'actions': {'total_actions': 0, 'completed_actions': 0},
                }
            }
    
    def _calculate_risk_compliance_correlation(self):
        """
        Calculate correlation metrics between risk management and compliance activities.
        This provides insights into how risk mitigation aligns with compliance efforts.
        """
        try:
            # Count risks that have associated compliance actions
            total_risks = Risk.objects.count()
            risks_with_actions = Risk.objects.filter(riskaction__isnull=False).distinct().count()
            
            # Count overdue risks vs overdue assessments for comparative analysis
            overdue_risks = Risk.objects.filter(
                review_date__lt=timezone.now().date(),
                status__in=['identified', 'assessed', 'treatment_planned']
            ).count()
            
            # Calculate action completion rate for risk mitigation
            total_risk_actions = RiskAction.objects.count()
            completed_risk_actions = RiskAction.objects.filter(status='completed').count()
            
            risk_action_completion_rate = (
                completed_risk_actions / total_risk_actions * 100
            ) if total_risk_actions > 0 else 0
            
            return {
                'total_risks': total_risks,
                'risks_with_mitigation_actions': risks_with_actions,
                'risk_mitigation_coverage': (
                    risks_with_actions / total_risks * 100
                ) if total_risks > 0 else 0,
                'overdue_risks': overdue_risks,
                'total_risk_actions': total_risk_actions,
                'completed_risk_actions': completed_risk_actions,
                'risk_action_completion_rate': round(risk_action_completion_rate, 1),
                'integration_insights': {
                    'risk_driven_compliance': risks_with_actions > 0,
                    'action_based_mitigation': total_risk_actions > 0,
                    'comprehensive_coverage': (
                        risks_with_actions / total_risks > 0.7
                    ) if total_risks > 0 else False,
                }
            }
        except Exception:
            return {
                'total_risks': 0,
                'risks_with_mitigation_actions': 0,
                'risk_mitigation_coverage': 0,
                'integration_insights': {
                    'risk_driven_compliance': False,
                    'action_based_mitigation': False,
                    'comprehensive_coverage': False,
                }
            }
    
    def _generate_risk_analytics_report(self):
        """Generate comprehensive risk analytics report HTML."""
        context = {
            'report': self.report,
            'generated_at': timezone.now(),
        }
        
        # Get comprehensive risk analytics data
        risk_context = self._get_risk_analytics_context()
        context.update(risk_context)
        
        # Get additional risk analytics data for detailed report
        try:
            context.update({
                'trend_analysis': RiskAnalyticsService.get_risk_trend_analysis(),
                'control_integration': RiskAnalyticsService.get_risk_control_integration_analysis(),
                'dashboard_data': RiskReportGenerator.generate_risk_dashboard_data(),
            })
        except Exception as e:
            context['analytics_error'] = str(e)
        
        return render_to_string('exports/reports/risk_analytics.html', context)