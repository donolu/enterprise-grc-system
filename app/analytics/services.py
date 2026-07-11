"""
Cross-Module Analytics and Reporting Services

Provides comprehensive analytics across all GRC modules including compliance,
risk management, vendor tracking, policy management, and training programs.
"""

from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Count, Q, Avg, Sum, F, Case, When, Value, CharField, IntegerField
from django.db.models.functions import TruncMonth, TruncWeek, Coalesce
from django.utils import timezone
from django.contrib.auth import get_user_model
from collections import defaultdict
import json

# Import models from all modules
from risk.models import Risk, RiskCategory, RiskAction
from catalogs.models import Framework, Control, ControlAssessment, AssessmentEvidence
from policies.models import Policy, PolicyVersion, PolicyAcknowledgment, PolicyDistribution
from vendors.models import Vendor, VendorTask
from training.models import TrainingVideo, TrainingCategory, SecurityAwarenessCampaign, VideoView

# Use ControlAssessment as our main assessment model
Assessment = ControlAssessment
try:
    from vendors.models import VendorAssessment
except ImportError:
    VendorAssessment = None

User = get_user_model()


class CrossModuleAnalyticsService:
    """
    Comprehensive analytics service providing cross-module insights and
    executive-level reporting for the entire GRC platform.
    """

    @staticmethod
    def get_executive_dashboard_data():
        """
        Get executive dashboard data with key metrics across all modules.

        Returns:
            dict: Executive-level metrics and KPIs
        """
        now = timezone.now().date()
        quarter_ago = now - timedelta(days=90)

        # Risk metrics
        risk_metrics = {
            'total_risks': Risk.objects.count(),
            'active_risks': Risk.objects.exclude(status__in=['closed', 'transferred']).count(),
            'critical_high_risks': Risk.objects.filter(
                risk_level__in=['critical', 'high']
            ).exclude(status__in=['closed', 'transferred']).count(),
            'overdue_actions': RiskAction.objects.filter(
                due_date__lt=now,
                status__in=['pending', 'in_progress', 'deferred']
            ).count()
        }

        # Compliance metrics
        compliance_metrics = {
            'total_assessments': Assessment.objects.count(),
            'active_assessments': Assessment.objects.filter(status='in_progress').count(),
            'completed_assessments': Assessment.objects.filter(status='complete').count(),
            'overdue_assessments': Assessment.objects.filter(
                due_date__lt=now,
                status__in=['not_started', 'in_progress']
            ).count(),
            'avg_completion_rate': Assessment.objects.filter(
                status='complete'
            ).aggregate(avg_score=Avg('compliance_score'))['avg_score'] or 0
        }

        # Policy metrics
        policy_metrics = {
            'total_policies': Policy.objects.count(),
            'active_policies': Policy.objects.filter(status='active').count(),
            'pending_acknowledgments': PolicyDistribution.objects.filter(
                acknowledgments__isnull=True
            ).count(),
            'overdue_acknowledgments': PolicyDistribution.objects.filter(
                acknowledgments__isnull=True,
                is_overdue=True
            ).count(),
            'acknowledgment_rate': 0  # Will calculate below
        }

        # Calculate acknowledgment rate
        total_distributions = PolicyDistribution.objects.count()
        acknowledged_distributions = PolicyDistribution.objects.filter(
            acknowledgments__isnull=False
        ).count()
        if total_distributions > 0:
            policy_metrics['acknowledgment_rate'] = round(
                (acknowledged_distributions / total_distributions) * 100, 1
            )

        # Vendor metrics
        vendor_metrics = {
            'total_vendors': Vendor.objects.count(),
            'active_vendors': Vendor.objects.filter(status='active').count(),
            'high_risk_vendors': Vendor.objects.filter(risk_level='high').count(),
            'contracts_expiring_soon': Vendor.objects.filter(
                contract_end_date__lte=now + timedelta(days=90),
                contract_end_date__gte=now,
                status='active'
            ).count(),
            'overdue_tasks': VendorTask.objects.filter(
                due_date__lt=now,
                status__in=['pending', 'in_progress']
            ).count()
        }

        # Training metrics
        training_metrics = {
            'total_videos': TrainingVideo.objects.count(),
            'total_views': VideoView.objects.count(),
            'unique_viewers': VideoView.objects.values('user').distinct().count(),
            'completion_rate': 0,  # Will calculate below
            'active_campaigns': SecurityAwarenessCampaign.objects.filter(
                is_active=True
            ).count()
        }

        # Calculate training completion rate
        total_views = VideoView.objects.count()
        completed_views = VideoView.objects.filter(completed=True).count()
        if total_views > 0:
            training_metrics['completion_rate'] = round(
                (completed_views / total_views) * 100, 1
            )

        return {
            'risk_summary': risk_metrics,
            'compliance_summary': compliance_metrics,
            'policy_summary': policy_metrics,
            'vendor_summary': vendor_metrics,
            'training_summary': training_metrics,
            'generated_at': now.isoformat(),
            'report_period': {
                'start_date': quarter_ago.isoformat(),
                'end_date': now.isoformat()
            }
        }

    @staticmethod
    def get_compliance_dashboard_data():
        """
        Get comprehensive compliance dashboard metrics and trends.

        Returns:
            dict: Compliance-focused analytics
        """
        now = timezone.now().date()

        # Framework completion rates
        framework_stats = list(Framework.objects.annotate(
            total_assessments=Count('assessment_set'),
            completed_assessments=Count(
                Case(When(assessment_set__status='complete', then=1))
            ),
            in_progress_assessments=Count(
                Case(When(assessment_set__status='in_progress', then=1))
            ),
            overdue_assessments=Count(
                Case(
                    When(
                        Q(assessment_set__due_date__lt=now) &
                        Q(assessment_set__status__in=['not_started', 'in_progress']),
                        then=1
                    )
                )
            ),
            avg_score=Avg('assessment_set__compliance_score')
        ).values(
            'name', 'framework_type', 'total_assessments', 'completed_assessments',
            'in_progress_assessments', 'overdue_assessments', 'avg_score'
        ))

        # Calculate completion rates
        for framework in framework_stats:
            if framework['total_assessments'] > 0:
                framework['completion_rate'] = round(
                    (framework['completed_assessments'] / framework['total_assessments']) * 100, 1
                )
            else:
                framework['completion_rate'] = 0

        # Control effectiveness analysis
        control_effectiveness = list(Control.objects.annotate(
            assessment_count=Count('controlassessment'),
            avg_maturity=Avg('controlassessment__maturity_level'),
            avg_effectiveness=Avg('controlassessment__effectiveness_rating'),
            high_risk_count=Count(
                Case(When(controlassessment__risk_rating__gte=7, then=1))
            )
        ).values(
            'control_type', 'automation_level', 'assessment_count',
            'avg_maturity', 'avg_effectiveness', 'high_risk_count'
        ).order_by('-assessment_count'))

        # Assessment progress trends (last 6 months)
        six_months_ago = now - timedelta(days=180)
        assessment_trends = list(Assessment.objects.filter(
            created_at__date__gte=six_months_ago
        ).extra(
            select={'month': 'DATE_TRUNC(\'month\', created_at)'}
        ).values('month').annotate(
            created=Count('id'),
            completed=Count(Case(When(status='complete', then=1))),
            avg_score=Avg('compliance_score')
        ).order_by('month'))

        # Evidence collection metrics
        evidence_stats = {
            'total_evidence': AssessmentEvidence.objects.count(),
            'validated_evidence': AssessmentEvidence.objects.filter(is_validated=True).count(),
            'evidence_by_type': dict(AssessmentEvidence.objects.values('evidence_type').annotate(
                count=Count('id')
            ).values_list('evidence_type', 'count')),
            'assessments_with_evidence': Assessment.objects.filter(
                evidence__isnull=False
            ).distinct().count()
        }

        return {
            'framework_statistics': framework_stats,
            'control_effectiveness': control_effectiveness,
            'assessment_trends': assessment_trends,
            'evidence_statistics': evidence_stats,
            'overall_metrics': {
                'total_frameworks': Framework.objects.count(),
                'active_frameworks': Framework.objects.filter(status='active').count(),
                'total_controls': Control.objects.count(),
                'automated_controls': Control.objects.filter(automation_level='automated').count(),
                'avg_maturity_score': Control.objects.aggregate(
                    avg=Avg('controlassessment__maturity_level')
                )['avg'] or 0
            },
            'generated_at': now.isoformat()
        }

    @staticmethod
    def get_vendor_risk_dashboard_data():
        """
        Get vendor management and risk assessment dashboard data.

        Returns:
            dict: Vendor-focused analytics and risk metrics
        """
        now = timezone.now().date()

        # Vendor risk distribution
        vendor_risk_stats = {
            'risk_distribution': dict(Vendor.objects.values('risk_level').annotate(
                count=Count('id'),
                total_spend=Sum('annual_spend'),
                avg_performance=Avg('performance_score')
            ).values_list('risk_level', 'count')),
            'total_vendors': Vendor.objects.count(),
            'active_vendors': Vendor.objects.filter(status='active').count(),
            'total_annual_spend': Vendor.objects.aggregate(
                total=Sum('annual_spend')
            )['total'] or 0,
            'avg_performance_score': Vendor.objects.aggregate(
                avg=Avg('performance_score')
            )['avg'] or 0
        }

        # Contract management metrics
        contract_metrics = {
            'expiring_30_days': Vendor.objects.filter(
                contract_end_date__lte=now + timedelta(days=30),
                contract_end_date__gte=now,
                status='active'
            ).count(),
            'expiring_90_days': Vendor.objects.filter(
                contract_end_date__lte=now + timedelta(days=90),
                contract_end_date__gte=now,
                status='active'
            ).count(),
            'expired_contracts': Vendor.objects.filter(
                contract_end_date__lt=now,
                status='active'
            ).count(),
            'renewals_needed': Vendor.objects.filter(
                contract_end_date__lte=now + timedelta(days=180),
                contract_end_date__gte=now,
                status='active'
            ).count()
        }

        # Vendor task analysis
        task_analytics = {
            'total_tasks': VendorTask.objects.count(),
            'overdue_tasks': VendorTask.objects.filter(
                due_date__lt=now,
                status__in=['pending', 'in_progress']
            ).count(),
            'due_this_week': VendorTask.objects.filter(
                due_date__gte=now,
                due_date__lte=now + timedelta(days=7),
                status__in=['pending', 'in_progress']
            ).count(),
            'task_type_distribution': dict(VendorTask.objects.values('task_type').annotate(
                count=Count('id')
            ).values_list('task_type', 'count')),
            'completion_rate': 0
        }

        # Calculate task completion rate
        total_tasks = VendorTask.objects.count()
        completed_tasks = VendorTask.objects.filter(status='completed').count()
        if total_tasks > 0:
            task_analytics['completion_rate'] = round(
                (completed_tasks / total_tasks) * 100, 1
            )

        # Top vendors by spend and risk
        top_vendors = list(Vendor.objects.values(
            'name', 'risk_level', 'annual_spend', 'performance_score',
            'contract_end_date', 'status'
        ).order_by('-annual_spend')[:10])

        # High-risk vendor analysis
        high_risk_vendors = list(Vendor.objects.filter(
            risk_level='high'
        ).values(
            'name', 'annual_spend', 'performance_score', 'contract_end_date'
        ).annotate(
            open_tasks=Count('vendortask', filter=Q(vendortask__status__in=['pending', 'in_progress']))
        ).order_by('-annual_spend'))

        return {
            'vendor_risk_statistics': vendor_risk_stats,
            'contract_management': contract_metrics,
            'task_analytics': task_analytics,
            'top_vendors': top_vendors,
            'high_risk_vendors': high_risk_vendors,
            'generated_at': now.isoformat()
        }

    @staticmethod
    def get_policy_management_dashboard_data():
        """
        Get policy management and acknowledgment tracking dashboard data.

        Returns:
            dict: Policy-focused analytics and compliance metrics
        """
        now = timezone.now().date()

        # Policy distribution metrics
        policy_stats = {
            'total_policies': Policy.objects.count(),
            'active_policies': Policy.objects.filter(status='active').count(),
            'policies_requiring_acknowledgment': Policy.objects.filter(
                requires_acknowledgment=True
            ).count(),
            'draft_policies': Policy.objects.filter(status='draft').count(),
            'under_review_policies': Policy.objects.filter(status='under_review').count()
        }

        # Acknowledgment analytics
        total_distributions = PolicyDistribution.objects.count()
        acknowledged_distributions = PolicyDistribution.objects.filter(
            acknowledgments__isnull=False
        ).distinct().count()

        acknowledgment_stats = {
            'total_distributions': total_distributions,
            'acknowledged_distributions': acknowledged_distributions,
            'pending_acknowledgments': total_distributions - acknowledged_distributions,
            'overdue_acknowledgments': PolicyDistribution.objects.filter(
                acknowledgments__isnull=True,
                is_overdue=True
            ).count(),
            'acknowledgment_rate': round(
                (acknowledged_distributions / max(total_distributions, 1)) * 100, 1
            )
        }

        # Policy category analysis
        category_stats = list(Policy.objects.values('category').annotate(
            policy_count=Count('id'),
            active_policies=Count(Case(When(status='active', then=1))),
            avg_acknowledgment_rate=Avg(
                Case(
                    When(
                        requires_acknowledgment=True,
                        then=F('policydistribution__acknowledgments__id')
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            )
        ).order_by('-policy_count'))

        # Recent policy activity (last 90 days)
        ninety_days_ago = now - timedelta(days=90)
        recent_activity = {
            'new_policies': Policy.objects.filter(created_at__date__gte=ninety_days_ago).count(),
            'updated_policies': PolicyVersion.objects.filter(
                created_at__date__gte=ninety_days_ago
            ).count(),
            'new_acknowledgments': PolicyAcknowledgment.objects.filter(
                acknowledged_at__date__gte=ninety_days_ago
            ).count(),
            'distributions_sent': PolicyDistribution.objects.filter(
                distributed_at__date__gte=ninety_days_ago
            ).count()
        }

        # Acknowledgment trends over time
        acknowledgment_trends = list(PolicyAcknowledgment.objects.filter(
            acknowledged_at__date__gte=now - timedelta(days=180)
        ).extra(
            select={'month': 'DATE_TRUNC(\'month\', acknowledged_at)'}
        ).values('month').annotate(
            acknowledgments=Count('id')
        ).order_by('month'))

        return {
            'policy_statistics': policy_stats,
            'acknowledgment_analytics': acknowledgment_stats,
            'category_breakdown': category_stats,
            'recent_activity': recent_activity,
            'acknowledgment_trends': acknowledgment_trends,
            'generated_at': now.isoformat()
        }

    @staticmethod
    def get_training_effectiveness_dashboard_data():
        """
        Get training program effectiveness and engagement analytics.

        Returns:
            dict: Training-focused metrics and engagement analysis
        """
        now = timezone.now().date()

        # Video engagement metrics
        video_stats = {
            'total_videos': TrainingVideo.objects.count(),
            'total_views': VideoView.objects.count(),
            'unique_viewers': VideoView.objects.values('user').distinct().count(),
            'total_watch_time': VideoView.objects.aggregate(
                total_minutes=Sum('duration_watched')
            )['total_minutes'] or 0,
            'avg_completion_rate': VideoView.objects.aggregate(
                avg_completion=Avg('completion_percentage')
            )['avg_completion'] or 0
        }

        # Category performance
        category_performance = list(TrainingCategory.objects.annotate(
            video_count=Count('trainingvideo'),
            total_views=Count('trainingvideo__videoview'),
            avg_completion=Avg('trainingvideo__videoview__completion_percentage'),
            total_watch_time=Sum('trainingvideo__videoview__duration_watched')
        ).values(
            'name', 'description', 'color', 'video_count', 'total_views',
            'avg_completion', 'total_watch_time'
        ).order_by('-total_views'))

        # User engagement analysis
        user_engagement = {
            'active_learners_30_days': VideoView.objects.filter(
                view_date__gte=now - timedelta(days=30)
            ).values('user').distinct().count(),
            'completed_videos_30_days': VideoView.objects.filter(
                view_date__gte=now - timedelta(days=30),
                completed=True
            ).count(),
            'avg_videos_per_user': VideoView.objects.values('user').annotate(
                video_count=Count('video', distinct=True)
            ).aggregate(avg=Avg('video_count'))['avg'] or 0,
            'completion_rate': 0
        }

        # Calculate overall completion rate
        total_views = VideoView.objects.count()
        completed_views = VideoView.objects.filter(completed=True).count()
        if total_views > 0:
            user_engagement['completion_rate'] = round(
                (completed_views / total_views) * 100, 1
            )

        # Security awareness campaign metrics
        campaign_stats = list(SecurityAwarenessCampaign.objects.annotate(
            engagement_rate=Case(
                When(total_sent=0, then=Value(0)),
                default=F('total_opened') * 100.0 / F('total_sent'),
                output_field=CharField()
            ),
            click_through_rate=Case(
                When(total_opened=0, then=Value(0)),
                default=F('total_clicked') * 100.0 / F('total_opened'),
                output_field=CharField()
            )
        ).values(
            'name', 'send_frequency', 'total_sent', 'total_opened',
            'total_clicked', 'engagement_rate', 'click_through_rate', 'is_active'
        ))

        # Training trends (last 6 months)
        six_months_ago = now - timedelta(days=180)
        training_trends = list(VideoView.objects.filter(
            view_date__gte=six_months_ago
        ).extra(
            select={'month': 'DATE_TRUNC(\'month\', view_date)'}
        ).values('month').annotate(
            views=Count('id'),
            unique_users=Count('user', distinct=True),
            completions=Count(Case(When(completed=True, then=1))),
            avg_completion_percentage=Avg('completion_percentage')
        ).order_by('month'))

        return {
            'video_engagement': video_stats,
            'category_performance': category_performance,
            'user_engagement': user_engagement,
            'campaign_analytics': campaign_stats,
            'training_trends': training_trends,
            'generated_at': now.isoformat()
        }

    @staticmethod
    def get_integrated_risk_posture():
        """
        Get integrated risk posture across all modules for executive reporting.

        Returns:
            dict: Cross-module risk analysis and correlations
        """
        now = timezone.now().date()

        # Risk sources across modules
        risk_sources = {
            'operational_risks': Risk.objects.exclude(status__in=['closed', 'transferred']).count(),
            'compliance_gaps': Assessment.objects.filter(
                status='complete',
                compliance_score__lt=70  # Assuming 70% is the compliance threshold
            ).count(),
            'vendor_risks': Vendor.objects.filter(risk_level__in=['high', 'critical']).count(),
            'policy_violations': PolicyDistribution.objects.filter(
                acknowledgments__isnull=True,
                is_overdue=True
            ).count(),
            'training_gaps': User.objects.exclude(
                videoview__completed=True
            ).count()
        }

        # Risk correlation analysis
        high_risk_vendors_with_assessments = Vendor.objects.filter(
            risk_level='high'
        ).annotate(
            assessment_count=Count('vendorassessment')
        ).values('name', 'annual_spend', 'assessment_count')

        # Compliance framework risk correlation
        framework_risk_correlation = list(Framework.objects.annotate(
            incomplete_assessments=Count(
                Case(
                    When(
                        Q(assessment_set__status__in=['not_started', 'in_progress']) &
                        Q(assessment_set__due_date__lt=now),
                        then=1
                    )
                )
            ),
            low_scoring_assessments=Count(
                Case(
                    When(
                        Q(assessment_set__status='complete') &
                        Q(assessment_set__compliance_score__lt=70),
                        then=1
                    )
                )
            ),
            related_risks=Count('assessment_set__risks', distinct=True)
        ).values(
            'name', 'framework_type', 'incomplete_assessments',
            'low_scoring_assessments', 'related_risks'
        ))

        # Risk velocity and trending
        thirty_days_ago = now - timedelta(days=30)
        risk_velocity = {
            'new_risks_30_days': Risk.objects.filter(
                created_at__date__gte=thirty_days_ago
            ).count(),
            'resolved_risks_30_days': Risk.objects.filter(
                closed_date__gte=thirty_days_ago,
                closed_date__isnull=False
            ).count(),
            'escalated_risks': Risk.objects.filter(
                created_at__date__gte=thirty_days_ago,
                risk_level__in=['high', 'critical']
            ).count(),
            'overdue_items': (
                RiskAction.objects.filter(
                    due_date__lt=now,
                    status__in=['pending', 'in_progress']
                ).count() +
                Assessment.objects.filter(
                    due_date__lt=now,
                    status__in=['not_started', 'in_progress']
                ).count() +
                VendorTask.objects.filter(
                    due_date__lt=now,
                    status__in=['pending', 'in_progress']
                ).count()
            )
        }

        # Risk maturity indicators
        risk_maturity = {
            'risk_treatment_coverage': Risk.objects.exclude(
                treatment_strategy__isnull=True
            ).exclude(treatment_strategy='').count() / max(Risk.objects.count(), 1) * 100,
            'control_automation_rate': Control.objects.filter(
                automation_level='automated'
            ).count() / max(Control.objects.count(), 1) * 100,
            'policy_acknowledgment_rate': (
                PolicyDistribution.objects.filter(
                    acknowledgments__isnull=False
                ).distinct().count() / max(PolicyDistribution.objects.count(), 1) * 100
            ),
            'vendor_assessment_coverage': Vendor.objects.filter(
                vendorassessment__isnull=False
            ).distinct().count() / max(Vendor.objects.count(), 1) * 100
        }

        return {
            'risk_source_analysis': risk_sources,
            'vendor_risk_correlation': list(high_risk_vendors_with_assessments),
            'framework_risk_correlation': framework_risk_correlation,
            'risk_velocity_metrics': risk_velocity,
            'risk_maturity_indicators': {
                'treatment_coverage': round(risk_maturity['risk_treatment_coverage'], 1),
                'automation_rate': round(risk_maturity['control_automation_rate'], 1),
                'acknowledgment_rate': round(risk_maturity['policy_acknowledgment_rate'], 1),
                'assessment_coverage': round(risk_maturity['vendor_assessment_coverage'], 1)
            },
            'overall_risk_score': round(sum(risk_sources.values()) / len(risk_sources), 1),
            'generated_at': now.isoformat()
        }


class AnalyticsReportGenerator:
    """
    Analytics report generation service for creating comprehensive
    cross-module analytics reports and dashboard data.
    """

    @staticmethod
    def generate_executive_report_data():
        """
        Generate comprehensive executive report data for leadership.

        Returns:
            dict: Complete executive analytics package
        """
        return {
            'executive_dashboard': CrossModuleAnalyticsService.get_executive_dashboard_data(),
            'integrated_risk_posture': CrossModuleAnalyticsService.get_integrated_risk_posture(),
            'compliance_overview': CrossModuleAnalyticsService.get_compliance_dashboard_data(),
            'vendor_risk_summary': CrossModuleAnalyticsService.get_vendor_risk_dashboard_data(),
            'policy_compliance': CrossModuleAnalyticsService.get_policy_management_dashboard_data(),
            'training_effectiveness': CrossModuleAnalyticsService.get_training_effectiveness_dashboard_data(),
            'report_metadata': {
                'generated_at': timezone.now().isoformat(),
                'report_type': 'executive_comprehensive',
                'version': '1.0'
            }
        }

    @staticmethod
    def generate_operational_dashboard_data():
        """
        Generate operational dashboard data for day-to-day management.

        Returns:
            dict: Operational analytics focused on actionable metrics
        """
        # Import risk analytics for integration
        from risk.analytics import RiskAnalyticsService

        return {
            'risk_analytics': RiskAnalyticsService.get_risk_overview_stats(),
            'compliance_metrics': CrossModuleAnalyticsService.get_compliance_dashboard_data(),
            'vendor_management': CrossModuleAnalyticsService.get_vendor_risk_dashboard_data(),
            'policy_tracking': CrossModuleAnalyticsService.get_policy_management_dashboard_data(),
            'training_progress': CrossModuleAnalyticsService.get_training_effectiveness_dashboard_data(),
            'report_metadata': {
                'generated_at': timezone.now().isoformat(),
                'report_type': 'operational_dashboard',
                'version': '1.0'
            }
        }