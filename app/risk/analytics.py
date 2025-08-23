"""
Risk Analytics and Reporting Service

Provides comprehensive risk analytics, trend analysis, and reporting capabilities
for risk management dashboard and executive reporting.
"""

from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Count, Q, Avg, Sum, F, Case, When, Value, CharField, IntegerField
from django.db.models.functions import TruncMonth, TruncWeek, Coalesce
from django.utils import timezone
from django.contrib.auth import get_user_model
from collections import defaultdict
import json

from .models import Risk, RiskCategory, RiskAction, RiskActionEvidence, RiskMatrix

User = get_user_model()


class RiskAnalyticsService:
    """
    Comprehensive risk analytics service providing data aggregation,
    trend analysis, and reporting capabilities.
    """
    
    @staticmethod
    def get_risk_overview_stats():
        """
        Get comprehensive risk overview statistics for dashboard.
        
        Returns:
            dict: Risk overview statistics including counts, distributions, and trends
        """
        now = timezone.now().date()
        thirty_days_ago = now - timedelta(days=30)
        
        # Basic risk counts
        total_risks = Risk.objects.count()
        active_risks = Risk.objects.exclude(status__in=['closed', 'transferred']).count()
        
        # Risk level distribution
        risk_level_dist = dict(Risk.objects.values('risk_level').annotate(
            count=Count('id')
        ).values_list('risk_level', 'count'))
        
        # Status distribution  
        status_dist = dict(Risk.objects.values('status').annotate(
            count=Count('id')
        ).values_list('status', 'count'))
        
        # Recent activity
        recent_risks = Risk.objects.filter(created_at__date__gte=thirty_days_ago).count()
        overdue_reviews = Risk.objects.filter(
            next_review_date__lt=now,
            next_review_date__isnull=False
        ).exclude(status__in=['closed', 'transferred']).count()
        
        # Average risk score
        avg_risk_score = Risk.objects.aggregate(
            avg_score=Avg(F('impact') * F('likelihood'))
        )['avg_score'] or 0
        
        # Category distribution
        category_dist = list(Risk.objects.values(
            'category__name', 'category__color'
        ).annotate(
            count=Count('id'),
            avg_score=Avg(F('impact') * F('likelihood'))
        ).order_by('-count'))
        
        # Treatment strategy distribution
        treatment_dist = dict(Risk.objects.exclude(
            treatment_strategy__isnull=True
        ).exclude(
            treatment_strategy=''
        ).values('treatment_strategy').annotate(
            count=Count('id')
        ).values_list('treatment_strategy', 'count'))
        
        return {
            'total_risks': total_risks,
            'active_risks': active_risks,
            'closed_risks': total_risks - active_risks,
            'recent_risks': recent_risks,
            'overdue_reviews': overdue_reviews,
            'average_risk_score': round(float(avg_risk_score), 2),
            'risk_level_distribution': risk_level_dist,
            'status_distribution': status_dist,
            'category_distribution': category_dist,
            'treatment_distribution': treatment_dist,
            'generated_at': now.isoformat()
        }
    
    @staticmethod
    def get_risk_action_overview_stats():
        """
        Get comprehensive risk action statistics for dashboard.
        
        Returns:
            dict: Risk action overview statistics and progress metrics
        """
        now = timezone.now().date()
        
        # Basic action counts
        total_actions = RiskAction.objects.count()
        active_actions = RiskAction.objects.exclude(status__in=['completed', 'cancelled']).count()
        completed_actions = RiskAction.objects.filter(status='completed').count()
        
        # Status distribution
        status_dist = dict(RiskAction.objects.values('status').annotate(
            count=Count('id')
        ).values_list('status', 'count'))
        
        # Priority distribution
        priority_dist = dict(RiskAction.objects.values('priority').annotate(
            count=Count('id')
        ).values_list('priority', 'count'))
        
        # Action type distribution
        action_type_dist = dict(RiskAction.objects.values('action_type').annotate(
            count=Count('id')
        ).values_list('action_type', 'count'))
        
        # Due date analysis
        overdue_actions = RiskAction.objects.filter(
            due_date__lt=now,
            status__in=['pending', 'in_progress', 'deferred']
        ).count()
        
        due_this_week = RiskAction.objects.filter(
            due_date__gte=now,
            due_date__lte=now + timedelta(days=7),
            status__in=['pending', 'in_progress', 'deferred']
        ).count()
        
        # Progress metrics
        avg_progress = RiskAction.objects.exclude(
            status='completed'
        ).aggregate(
            avg_progress=Avg('progress_percentage')
        )['avg_progress'] or 0
        
        # Completion rate
        completion_rate = 0
        if total_actions > 0:
            completion_rate = (completed_actions / total_actions) * 100
        
        # Actions by assignee
        assignee_stats = list(RiskAction.objects.values(
            'assigned_to__first_name', 'assigned_to__last_name', 'assigned_to__username'
        ).annotate(
            total_assigned=Count('id'),
            completed=Count(Case(When(status='completed', then=1))),
            overdue=Count(Case(
                When(
                    Q(due_date__lt=now) & Q(status__in=['pending', 'in_progress', 'deferred']),
                    then=1
                )
            )),
            avg_progress=Avg('progress_percentage')
        ).order_by('-total_assigned')[:10])
        
        return {
            'total_actions': total_actions,
            'active_actions': active_actions,
            'completed_actions': completed_actions,
            'overdue_actions': overdue_actions,
            'due_this_week': due_this_week,
            'average_progress': round(float(avg_progress), 2),
            'completion_rate': round(completion_rate, 2),
            'status_distribution': status_dist,
            'priority_distribution': priority_dist,
            'action_type_distribution': action_type_dist,
            'top_assignees': assignee_stats,
            'generated_at': now.isoformat()
        }
    
    @staticmethod
    def get_risk_trend_analysis(days=90):
        """
        Get risk trend analysis over specified time period.
        
        Args:
            days: Number of days to analyze (default: 90)
            
        Returns:
            dict: Risk trend data including creation, resolution, and level changes
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Risk creation trend
        creation_trend = list(Risk.objects.filter(
            created_at__date__gte=start_date
        ).extra(
            select={'month': 'DATE_TRUNC(\'month\', created_at)'}
        ).values('month').annotate(
            count=Count('id'),
            critical=Count(Case(When(risk_level='critical', then=1))),
            high=Count(Case(When(risk_level='high', then=1))),
            medium=Count(Case(When(risk_level='medium', then=1))),
            low=Count(Case(When(risk_level='low', then=1)))
        ).order_by('month'))
        
        # Risk closure trend
        closure_trend = list(Risk.objects.filter(
            closed_date__gte=start_date,
            closed_date__isnull=False
        ).extra(
            select={'month': 'DATE_TRUNC(\'month\', closed_date)'}
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month'))
        
        # Active risk count over time (snapshot at month end)
        active_trend = []
        current_date = start_date.replace(day=1)
        while current_date <= end_date:
            month_end = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            if month_end > end_date:
                month_end = end_date
                
            active_count = Risk.objects.filter(
                created_at__date__lte=month_end
            ).exclude(
                closed_date__lte=month_end
            ).count()
            
            active_trend.append({
                'month': current_date.isoformat(),
                'active_risks': active_count
            })
            
            current_date = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        
        return {
            'period_days': days,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'creation_trend': creation_trend,
            'closure_trend': closure_trend,
            'active_trend': active_trend,
            'generated_at': timezone.now().isoformat()
        }
    
    @staticmethod
    def get_risk_action_progress_analysis():
        """
        Get detailed analysis of risk action progress and effectiveness.
        
        Returns:
            dict: Action progress analysis including velocity and bottlenecks
        """
        now = timezone.now().date()
        thirty_days_ago = now - timedelta(days=30)
        
        # Action velocity (completed actions per month)
        velocity_data = list(RiskAction.objects.filter(
            completed_date__isnull=False,
            completed_date__gte=now - timedelta(days=180)
        ).extra(
            select={'month': 'DATE_TRUNC(\'month\', completed_date)'}
        ).values('month').annotate(
            completed=Count('id'),
            avg_days_to_complete=Avg(
                F('completed_date') - F('created_at__date')
            )
        ).order_by('month'))
        
        # Actions by risk level
        risk_level_actions = list(RiskAction.objects.values(
            'risk__risk_level'
        ).annotate(
            total_actions=Count('id'),
            completed=Count(Case(When(status='completed', then=1))),
            in_progress=Count(Case(When(status='in_progress', then=1))),
            overdue=Count(Case(
                When(
                    Q(due_date__lt=now) & Q(status__in=['pending', 'in_progress', 'deferred']),
                    then=1
                )
            )),
            avg_progress=Avg('progress_percentage')
        ).order_by('risk__risk_level'))
        
        # Evidence collection analysis
        evidence_stats = {
            'total_evidence': RiskActionEvidence.objects.count(),
            'validated_evidence': RiskActionEvidence.objects.filter(is_validated=True).count(),
            'actions_with_evidence': RiskAction.objects.filter(evidence__isnull=False).distinct().count(),
            'evidence_by_type': dict(RiskActionEvidence.objects.values('evidence_type').annotate(
                count=Count('id')
            ).values_list('evidence_type', 'count'))
        }
        
        # Treatment effectiveness (risk level changes after actions)
        treatment_effectiveness = Risk.objects.filter(
            actions__status='completed'
        ).values(
            'treatment_strategy'
        ).annotate(
            risks_count=Count('id', distinct=True),
            total_actions=Count('actions'),
            avg_original_score=Avg(F('impact') * F('likelihood'))
        ).order_by('treatment_strategy')
        
        return {
            'action_velocity': velocity_data,
            'actions_by_risk_level': risk_level_actions,
            'evidence_statistics': evidence_stats,
            'treatment_effectiveness': list(treatment_effectiveness),
            'generated_at': now.isoformat()
        }
    
    @staticmethod
    def get_risk_heat_map_data():
        """
        Get risk heat map data for impact vs likelihood visualization.
        
        Returns:
            dict: Heat map data with risk counts by impact/likelihood combination
        """
        # Get the default risk matrix for reference
        default_matrix = RiskMatrix.objects.filter(is_default=True).first()
        if not default_matrix:
            # Create default 5x5 matrix data
            matrix_size = 5
        else:
            matrix_size = default_matrix.impact_levels
        
        # Initialize heat map data structure
        heat_map = {}
        for impact in range(1, matrix_size + 1):
            heat_map[impact] = {}
            for likelihood in range(1, matrix_size + 1):
                heat_map[impact][likelihood] = {
                    'count': 0,
                    'risk_level': 'low',
                    'risks': []
                }
        
        # Populate with actual risk data
        risks = Risk.objects.select_related('category', 'risk_owner').exclude(
            status__in=['closed', 'transferred']
        )
        
        for risk in risks:
            impact = min(max(1, risk.impact), matrix_size)
            likelihood = min(max(1, risk.likelihood), matrix_size)
            
            heat_map[impact][likelihood]['count'] += 1
            heat_map[impact][likelihood]['risk_level'] = risk.risk_level
            heat_map[impact][likelihood]['risks'].append({
                'id': risk.id,
                'risk_id': risk.risk_id,
                'title': risk.title,
                'category': risk.category.name if risk.category else 'Uncategorized',
                'owner': risk.risk_owner.get_full_name() if risk.risk_owner else 'Unassigned',
                'status': risk.status,
                'risk_score': risk.risk_score
            })
        
        # Calculate totals and percentages
        total_risks = sum(
            heat_map[i][j]['count'] 
            for i in range(1, matrix_size + 1) 
            for j in range(1, matrix_size + 1)
        )
        
        return {
            'matrix_size': matrix_size,
            'total_risks': total_risks,
            'heat_map': heat_map,
            'impact_labels': [f'Very Low', 'Low', 'Medium', 'High', 'Very High'][:matrix_size],
            'likelihood_labels': [f'Very Low', 'Low', 'Medium', 'High', 'Very High'][:matrix_size],
            'generated_at': timezone.now().date().isoformat()
        }
    
    @staticmethod
    def get_risk_control_integration_analysis():
        """
        Analyze integration between risks and control assessments.
        Note: This will be enhanced once control assessment integration is implemented.
        
        Returns:
            dict: Analysis of risk-control relationships and gaps
        """
        # For now, provide risk analysis that prepares for control integration
        risks_with_controls = Risk.objects.filter(
            current_controls__isnull=False
        ).exclude(current_controls='').count()
        
        risks_without_controls = Risk.objects.filter(
            Q(current_controls__isnull=True) | Q(current_controls='')
        ).count()
        
        # Analyze risks by category for control gap identification
        category_analysis = list(Risk.objects.values(
            'category__name'
        ).annotate(
            total_risks=Count('id'),
            high_critical_risks=Count(
                Case(When(risk_level__in=['high', 'critical'], then=1))
            ),
            risks_with_controls=Count(
                Case(
                    When(
                        Q(current_controls__isnull=False) & ~Q(current_controls=''),
                        then=1
                    )
                )
            ),
            avg_risk_score=Avg(F('impact') * F('likelihood'))
        ).order_by('-high_critical_risks'))
        
        return {
            'risks_with_controls': risks_with_controls,
            'risks_without_controls': risks_without_controls,
            'control_coverage_rate': round(
                (risks_with_controls / (risks_with_controls + risks_without_controls)) * 100, 2
            ) if (risks_with_controls + risks_without_controls) > 0 else 0,
            'category_control_analysis': category_analysis,
            'integration_status': 'basic_analysis',  # Will be 'full_integration' when enhanced
            'generated_at': timezone.now().date().isoformat()
        }
    
    @staticmethod
    def get_executive_risk_summary():
        """
        Get executive-level risk summary for leadership reporting.
        
        Returns:
            dict: High-level risk metrics and key insights for executives
        """
        now = timezone.now().date()
        quarter_ago = now - timedelta(days=90)
        
        # Key risk metrics
        total_risks = Risk.objects.count()
        active_risks = Risk.objects.exclude(status__in=['closed', 'transferred']).count()
        critical_high_risks = Risk.objects.filter(
            risk_level__in=['critical', 'high']
        ).exclude(status__in=['closed', 'transferred']).count()
        
        # Risk trend (quarterly)
        new_risks_quarter = Risk.objects.filter(created_at__date__gte=quarter_ago).count()
        closed_risks_quarter = Risk.objects.filter(
            closed_date__gte=quarter_ago,
            closed_date__isnull=False
        ).count()
        
        # Treatment progress
        total_actions = RiskAction.objects.count()
        completed_actions = RiskAction.objects.filter(status='completed').count()
        overdue_actions = RiskAction.objects.filter(
            due_date__lt=now,
            status__in=['pending', 'in_progress', 'deferred']
        ).count()
        
        # Top risk categories by exposure
        top_risk_categories = list(Risk.objects.values(
            'category__name'
        ).annotate(
            risk_count=Count('id'),
            critical_count=Count(Case(When(risk_level='critical', then=1))),
            high_count=Count(Case(When(risk_level='high', then=1))),
            avg_risk_score=Avg(F('impact') * F('likelihood')),
            total_exposure=Sum(F('impact') * F('likelihood'))
        ).order_by('-total_exposure')[:5])
        
        # Overdue review items
        overdue_reviews = Risk.objects.filter(
            next_review_date__lt=now,
            next_review_date__isnull=False
        ).exclude(status__in=['closed', 'transferred']).count()
        
        # Risk maturity indicators
        risks_with_treatment = Risk.objects.exclude(
            treatment_strategy__isnull=True
        ).exclude(treatment_strategy='').count()
        
        risks_with_controls = Risk.objects.filter(
            current_controls__isnull=False
        ).exclude(current_controls='').count()
        
        return {
            'risk_metrics': {
                'total_risks': total_risks,
                'active_risks': active_risks,
                'critical_high_risks': critical_high_risks,
                'risk_density': round(critical_high_risks / max(total_risks, 1) * 100, 1)
            },
            'quarterly_trend': {
                'new_risks': new_risks_quarter,
                'closed_risks': closed_risks_quarter,
                'net_change': new_risks_quarter - closed_risks_quarter
            },
            'treatment_progress': {
                'total_actions': total_actions,
                'completed_actions': completed_actions,
                'completion_rate': round(completed_actions / max(total_actions, 1) * 100, 1),
                'overdue_actions': overdue_actions
            },
            'top_risk_areas': top_risk_categories,
            'governance_indicators': {
                'overdue_reviews': overdue_reviews,
                'treatment_coverage': round(risks_with_treatment / max(active_risks, 1) * 100, 1),
                'control_coverage': round(risks_with_controls / max(active_risks, 1) * 100, 1)
            },
            'report_period': {
                'start_date': quarter_ago.isoformat(),
                'end_date': now.isoformat()
            },
            'generated_at': timezone.now().isoformat()
        }


class RiskReportGenerator:
    """
    Risk report generation service for creating comprehensive risk reports.
    Integrates with existing report generation infrastructure.
    """
    
    @staticmethod
    def generate_risk_dashboard_data():
        """
        Generate comprehensive dashboard data combining all analytics.
        
        Returns:
            dict: Complete dashboard data for frontend consumption
        """
        return {
            'risk_overview': RiskAnalyticsService.get_risk_overview_stats(),
            'action_overview': RiskAnalyticsService.get_risk_action_overview_stats(),
            'heat_map': RiskAnalyticsService.get_risk_heat_map_data(),
            'trend_analysis': RiskAnalyticsService.get_risk_trend_analysis(days=180),
            'progress_analysis': RiskAnalyticsService.get_risk_action_progress_analysis(),
            'control_integration': RiskAnalyticsService.get_risk_control_integration_analysis(),
            'executive_summary': RiskAnalyticsService.get_executive_risk_summary(),
            'generated_at': timezone.now().isoformat(),
            'dashboard_version': '1.0'
        }
    
    @staticmethod
    def get_risk_category_deep_dive(category_id=None):
        """
        Generate deep dive analysis for specific risk category.
        
        Args:
            category_id: ID of specific category to analyze (None for all)
            
        Returns:
            dict: Detailed category analysis
        """
        if category_id:
            category = RiskCategory.objects.get(id=category_id)
            risks = Risk.objects.filter(category=category)
            category_name = category.name
        else:
            risks = Risk.objects.all()
            category_name = "All Categories"
        
        # Category-specific metrics
        total_risks = risks.count()
        active_risks = risks.exclude(status__in=['closed', 'transferred']).count()
        
        risk_level_breakdown = dict(risks.values('risk_level').annotate(
            count=Count('id')
        ).values_list('risk_level', 'count'))
        
        status_breakdown = dict(risks.values('status').annotate(
            count=Count('id')
        ).values_list('status', 'count'))
        
        # Treatment analysis
        treatment_breakdown = dict(risks.exclude(
            treatment_strategy__isnull=True
        ).exclude(
            treatment_strategy=''
        ).values('treatment_strategy').annotate(
            count=Count('id')
        ).values_list('treatment_strategy', 'count'))
        
        # Action analysis for this category
        category_actions = RiskAction.objects.filter(risk__in=risks)
        action_stats = {
            'total_actions': category_actions.count(),
            'completed_actions': category_actions.filter(status='completed').count(),
            'overdue_actions': category_actions.filter(
                due_date__lt=timezone.now().date(),
                status__in=['pending', 'in_progress', 'deferred']
            ).count(),
            'avg_progress': category_actions.exclude(status='completed').aggregate(
                avg=Avg('progress_percentage')
            )['avg'] or 0
        }
        
        return {
            'category_name': category_name,
            'category_id': category_id,
            'risk_metrics': {
                'total_risks': total_risks,
                'active_risks': active_risks,
                'risk_level_breakdown': risk_level_breakdown,
                'status_breakdown': status_breakdown,
                'treatment_breakdown': treatment_breakdown
            },
            'action_metrics': action_stats,
            'generated_at': timezone.now().isoformat()
        }