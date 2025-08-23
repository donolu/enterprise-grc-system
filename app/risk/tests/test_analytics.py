import json
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock

from ..models import (
    Risk, RiskCategory, RiskMatrix, RiskAction, RiskActionEvidence,
    RiskActionReminderConfiguration
)
from ..analytics import RiskAnalyticsService, RiskReportGenerator

User = get_user_model()


class RiskAnalyticsServiceTest(TestCase):
    """Test cases for RiskAnalyticsService functionality."""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            first_name='User',
            last_name='One',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            first_name='User',
            last_name='Two',
            password='testpass123'
        )
        
        # Create risk categories
        self.security_category = RiskCategory.objects.create(
            name='Security',
            description='Information security risks',
            color='#dc3545'
        )
        self.compliance_category = RiskCategory.objects.create(
            name='Compliance',
            description='Regulatory compliance risks',
            color='#fd7e14'
        )
        
        # Create risk matrix
        self.risk_matrix = RiskMatrix.objects.create(
            name='Default Matrix',
            description='Standard 5x5 risk matrix',
            is_default=True,
            impact_levels=5,
            likelihood_levels=5
        )
        
        # Create test risks
        self.critical_risk = Risk.objects.create(
            title='Critical Security Breach',
            description='Potential for major security incident',
            category=self.security_category,
            impact=5,
            likelihood=4,
            risk_level='critical',
            status='assessed',
            treatment_strategy='mitigate',
            risk_owner=self.user1,
            identified_date=date.today() - timedelta(days=30),
            next_review_date=date.today() + timedelta(days=30),
            current_controls='Firewall, IDS'
        )
        
        self.high_risk = Risk.objects.create(
            title='Compliance Violation',
            description='Risk of regulatory non-compliance',
            category=self.compliance_category,
            impact=4,
            likelihood=3,
            risk_level='high',
            status='treatment_planned',
            treatment_strategy='mitigate',
            risk_owner=self.user2,
            identified_date=date.today() - timedelta(days=15),
            next_review_date=date.today() - timedelta(days=5)  # Overdue
        )
        
        self.medium_risk = Risk.objects.create(
            title='System Availability',
            description='Risk of system downtime',
            category=self.security_category,
            impact=3,
            likelihood=2,
            risk_level='medium',
            status='mitigated',
            treatment_strategy='accept',
            risk_owner=self.user1,
            identified_date=date.today() - timedelta(days=60)
        )
        
        self.closed_risk = Risk.objects.create(
            title='Legacy System Risk',
            description='Risks from legacy systems',
            category=self.security_category,
            impact=2,
            likelihood=1,
            risk_level='low',
            status='closed',
            treatment_strategy='transfer',
            risk_owner=self.user1,
            identified_date=date.today() - timedelta(days=90),
            closed_date=date.today() - timedelta(days=10)
        )
        
        # Create risk actions
        self.overdue_action = RiskAction.objects.create(
            risk=self.critical_risk,
            title='Implement Enhanced Firewall',
            description='Deploy next-gen firewall solution',
            action_type='mitigation',
            priority='critical',
            assigned_to=self.user1,
            status='in_progress',
            progress_percentage=75,
            due_date=date.today() - timedelta(days=3),
            start_date=date.today() - timedelta(days=30)
        )
        
        self.due_soon_action = RiskAction.objects.create(
            risk=self.high_risk,
            title='Update Compliance Policy',
            description='Review and update compliance documentation',
            action_type='mitigation',
            priority='high',
            assigned_to=self.user2,
            status='pending',
            progress_percentage=0,
            due_date=date.today() + timedelta(days=5),
            start_date=date.today()
        )
        
        self.completed_action = RiskAction.objects.create(
            risk=self.medium_risk,
            title='Deploy Monitoring Solution',
            description='Implement system monitoring',
            action_type='mitigation',
            priority='medium',
            assigned_to=self.user1,
            status='completed',
            progress_percentage=100,
            due_date=date.today() - timedelta(days=5),
            start_date=date.today() - timedelta(days=20),
            completed_date=date.today() - timedelta(days=2)
        )
        
        # Create evidence for completed action
        self.evidence = RiskActionEvidence.objects.create(
            action=self.completed_action,
            title='Monitoring Dashboard Screenshot',
            description='Screenshot showing active monitoring',
            evidence_type='screenshot',
            uploaded_by=self.user1,
            is_validated=True,
            validated_by=self.user2,
            validated_at=timezone.now()
        )
    
    def test_get_risk_overview_stats(self):
        """Test risk overview statistics generation."""
        overview = RiskAnalyticsService.get_risk_overview_stats()
        
        # Basic counts
        self.assertEqual(overview['total_risks'], 4)
        self.assertEqual(overview['active_risks'], 3)  # Excludes closed risk
        self.assertEqual(overview['closed_risks'], 1)
        self.assertEqual(overview['overdue_reviews'], 1)  # high_risk is overdue
        
        # Risk level distribution
        risk_levels = overview['risk_level_distribution']
        self.assertEqual(risk_levels.get('critical', 0), 1)
        self.assertEqual(risk_levels.get('high', 0), 1)
        self.assertEqual(risk_levels.get('medium', 0), 1)
        self.assertEqual(risk_levels.get('low', 0), 1)
        
        # Status distribution
        status_dist = overview['status_distribution']
        self.assertEqual(status_dist.get('assessed', 0), 1)
        self.assertEqual(status_dist.get('treatment_planned', 0), 1)
        self.assertEqual(status_dist.get('mitigated', 0), 1)
        self.assertEqual(status_dist.get('closed', 0), 1)
        
        # Treatment distribution
        treatment_dist = overview['treatment_distribution']
        self.assertEqual(treatment_dist.get('mitigate', 0), 2)
        self.assertEqual(treatment_dist.get('accept', 0), 1)
        self.assertEqual(treatment_dist.get('transfer', 0), 1)
        
        # Category distribution
        categories = overview['category_distribution']
        self.assertEqual(len(categories), 2)  # Security and Compliance
        
        # Average risk score should be calculated
        self.assertGreater(overview['average_risk_score'], 0)
        
        # Verify data structure
        self.assertIn('generated_at', overview)
        self.assertIsInstance(overview['recent_risks'], int)
    
    def test_get_risk_action_overview_stats(self):
        """Test risk action overview statistics generation."""
        action_overview = RiskAnalyticsService.get_risk_action_overview_stats()
        
        # Basic counts
        self.assertEqual(action_overview['total_actions'], 3)
        self.assertEqual(action_overview['active_actions'], 2)  # Excludes completed
        self.assertEqual(action_overview['completed_actions'], 1)
        self.assertEqual(action_overview['overdue_actions'], 1)  # overdue_action
        self.assertEqual(action_overview['due_this_week'], 1)  # due_soon_action
        
        # Progress metrics
        self.assertGreater(action_overview['average_progress'], 0)
        completion_rate = action_overview['completion_rate']
        self.assertAlmostEqual(completion_rate, 33.33, places=1)  # 1/3 completed
        
        # Status distribution
        status_dist = action_overview['status_distribution']
        self.assertEqual(status_dist.get('pending', 0), 1)
        self.assertEqual(status_dist.get('in_progress', 0), 1)
        self.assertEqual(status_dist.get('completed', 0), 1)
        
        # Priority distribution
        priority_dist = action_overview['priority_distribution']
        self.assertEqual(priority_dist.get('critical', 0), 1)
        self.assertEqual(priority_dist.get('high', 0), 1)
        self.assertEqual(priority_dist.get('medium', 0), 1)
        
        # Action type distribution
        action_type_dist = action_overview['action_type_distribution']
        self.assertEqual(action_type_dist.get('mitigation', 0), 3)
        
        # Top assignees
        assignees = action_overview['top_assignees']
        self.assertEqual(len(assignees), 2)  # user1 and user2
        
        # Verify data structure
        self.assertIn('generated_at', action_overview)
    
    def test_get_risk_trend_analysis(self):
        """Test risk trend analysis functionality."""
        # Test 90-day trend analysis
        trends = RiskAnalyticsService.get_risk_trend_analysis(days=90)
        
        # Basic structure validation
        self.assertEqual(trends['period_days'], 90)
        self.assertIn('start_date', trends)
        self.assertIn('end_date', trends)
        self.assertIn('creation_trend', trends)
        self.assertIn('closure_trend', trends)
        self.assertIn('active_trend', trends)
        self.assertIn('generated_at', trends)
        
        # Creation trend should include our risks
        creation_trend = trends['creation_trend']
        self.assertIsInstance(creation_trend, list)
        
        # Closure trend should include closed risk
        closure_trend = trends['closure_trend']
        self.assertIsInstance(closure_trend, list)
        
        # Active trend should show progression
        active_trend = trends['active_trend']
        self.assertIsInstance(active_trend, list)
        self.assertGreater(len(active_trend), 0)
    
    def test_get_risk_action_progress_analysis(self):
        """Test risk action progress analysis."""
        progress_analysis = RiskAnalyticsService.get_risk_action_progress_analysis()
        
        # Velocity data structure
        self.assertIn('action_velocity', progress_analysis)
        self.assertIsInstance(progress_analysis['action_velocity'], list)
        
        # Actions by risk level
        risk_level_actions = progress_analysis['actions_by_risk_level']
        self.assertIsInstance(risk_level_actions, list)
        
        # Evidence statistics
        evidence_stats = progress_analysis['evidence_statistics']
        self.assertEqual(evidence_stats['total_evidence'], 1)
        self.assertEqual(evidence_stats['validated_evidence'], 1)
        self.assertEqual(evidence_stats['actions_with_evidence'], 1)
        
        evidence_by_type = evidence_stats['evidence_by_type']
        self.assertEqual(evidence_by_type.get('screenshot', 0), 1)
        
        # Treatment effectiveness
        treatment_effectiveness = progress_analysis['treatment_effectiveness']
        self.assertIsInstance(treatment_effectiveness, list)
        
        # Generated timestamp
        self.assertIn('generated_at', progress_analysis)
    
    def test_get_risk_heat_map_data(self):
        """Test risk heat map data generation."""
        heat_map = RiskAnalyticsService.get_risk_heat_map_data()
        
        # Basic structure
        self.assertEqual(heat_map['matrix_size'], 5)  # Default matrix
        self.assertEqual(heat_map['total_risks'], 3)  # Excludes closed risk
        
        # Heat map data structure
        heat_map_data = heat_map['heat_map']
        self.assertIsInstance(heat_map_data, dict)
        
        # Check specific risk positions
        # critical_risk: impact=5, likelihood=4
        critical_cell = heat_map_data[5][4]
        self.assertEqual(critical_cell['count'], 1)
        self.assertEqual(critical_cell['risk_level'], 'critical')
        self.assertEqual(len(critical_cell['risks']), 1)
        self.assertEqual(critical_cell['risks'][0]['title'], 'Critical Security Breach')
        
        # Labels
        self.assertEqual(len(heat_map['impact_labels']), 5)
        self.assertEqual(len(heat_map['likelihood_labels']), 5)
        
        # Generated timestamp
        self.assertIn('generated_at', heat_map)
    
    def test_get_risk_control_integration_analysis(self):
        """Test risk-control integration analysis (basic version)."""
        integration = RiskAnalyticsService.get_risk_control_integration_analysis()
        
        # Control coverage metrics
        self.assertEqual(integration['risks_with_controls'], 1)  # Only critical_risk has controls
        self.assertEqual(integration['risks_without_controls'], 3)
        
        # Coverage rate calculation
        expected_rate = (1 / 4) * 100  # 25%
        self.assertAlmostEqual(integration['control_coverage_rate'], expected_rate, places=1)
        
        # Category analysis
        category_analysis = integration['category_control_analysis']
        self.assertIsInstance(category_analysis, list)
        self.assertGreaterEqual(len(category_analysis), 1)
        
        # Integration status
        self.assertEqual(integration['integration_status'], 'basic_analysis')
        
        # Generated timestamp
        self.assertIn('generated_at', integration)
    
    def test_get_executive_risk_summary(self):
        """Test executive risk summary generation."""
        executive_summary = RiskAnalyticsService.get_executive_risk_summary()
        
        # Risk metrics
        risk_metrics = executive_summary['risk_metrics']
        self.assertEqual(risk_metrics['total_risks'], 4)
        self.assertEqual(risk_metrics['active_risks'], 3)
        self.assertEqual(risk_metrics['critical_high_risks'], 2)
        self.assertGreater(risk_metrics['risk_density'], 0)
        
        # Quarterly trend (90 days)
        quarterly_trend = executive_summary['quarterly_trend']
        self.assertIn('new_risks', quarterly_trend)
        self.assertIn('closed_risks', quarterly_trend)
        self.assertIn('net_change', quarterly_trend)
        
        # Treatment progress
        treatment_progress = executive_summary['treatment_progress']
        self.assertEqual(treatment_progress['total_actions'], 3)
        self.assertEqual(treatment_progress['completed_actions'], 1)
        self.assertAlmostEqual(treatment_progress['completion_rate'], 33.3, places=1)
        self.assertEqual(treatment_progress['overdue_actions'], 1)
        
        # Top risk areas
        top_risk_areas = executive_summary['top_risk_areas']
        self.assertIsInstance(top_risk_areas, list)
        self.assertLessEqual(len(top_risk_areas), 5)
        
        # Governance indicators
        governance = executive_summary['governance_indicators']
        self.assertEqual(governance['overdue_reviews'], 1)
        self.assertIn('treatment_coverage', governance)
        self.assertIn('control_coverage', governance)
        
        # Report period
        report_period = executive_summary['report_period']
        self.assertIn('start_date', report_period)
        self.assertIn('end_date', report_period)
        
        # Generated timestamp
        self.assertIn('generated_at', executive_summary)


class RiskReportGeneratorTest(TestCase):
    """Test cases for RiskReportGenerator functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.category = RiskCategory.objects.create(
            name='Test Category',
            description='Test category for reporting',
            color='#007bff'
        )
        
        self.risk = Risk.objects.create(
            title='Test Risk',
            description='Test risk for reporting',
            category=self.category,
            impact=3,
            likelihood=3,
            risk_level='medium',
            status='assessed',
            risk_owner=self.user
        )
    
    def test_generate_risk_dashboard_data(self):
        """Test comprehensive dashboard data generation."""
        dashboard_data = RiskReportGenerator.generate_risk_dashboard_data()
        
        # Verify all expected sections are present
        expected_sections = [
            'risk_overview', 'action_overview', 'heat_map', 'trend_analysis',
            'progress_analysis', 'control_integration', 'executive_summary'
        ]
        
        for section in expected_sections:
            self.assertIn(section, dashboard_data)
        
        # Verify metadata
        self.assertIn('generated_at', dashboard_data)
        self.assertEqual(dashboard_data['dashboard_version'], '1.0')
        
        # Verify each section contains expected data
        self.assertIn('total_risks', dashboard_data['risk_overview'])
        self.assertIn('total_actions', dashboard_data['action_overview'])
        self.assertIn('matrix_size', dashboard_data['heat_map'])
        self.assertIn('period_days', dashboard_data['trend_analysis'])
    
    def test_get_risk_category_deep_dive_specific(self):
        """Test category-specific deep dive analysis."""
        deep_dive = RiskReportGenerator.get_risk_category_deep_dive(self.category.id)
        
        # Category identification
        self.assertEqual(deep_dive['category_name'], 'Test Category')
        self.assertEqual(deep_dive['category_id'], self.category.id)
        
        # Risk metrics for this category
        risk_metrics = deep_dive['risk_metrics']
        self.assertEqual(risk_metrics['total_risks'], 1)
        self.assertEqual(risk_metrics['active_risks'], 1)
        
        # Risk level breakdown
        risk_level_breakdown = risk_metrics['risk_level_breakdown']
        self.assertEqual(risk_level_breakdown.get('medium', 0), 1)
        
        # Status breakdown
        status_breakdown = risk_metrics['status_breakdown']
        self.assertEqual(status_breakdown.get('assessed', 0), 1)
        
        # Action metrics
        action_metrics = deep_dive['action_metrics']
        self.assertEqual(action_metrics['total_actions'], 0)  # No actions created
        
        # Generated timestamp
        self.assertIn('generated_at', deep_dive)
    
    def test_get_risk_category_deep_dive_all(self):
        """Test deep dive analysis for all categories."""
        deep_dive = RiskReportGenerator.get_risk_category_deep_dive(category_id=None)
        
        # Should analyze all categories
        self.assertEqual(deep_dive['category_name'], 'All Categories')
        self.assertIsNone(deep_dive['category_id'])
        
        # Should include all risks
        risk_metrics = deep_dive['risk_metrics']
        self.assertGreaterEqual(risk_metrics['total_risks'], 1)
        
        # Generated timestamp
        self.assertIn('generated_at', deep_dive)


class RiskAnalyticsAPITest(APITestCase):
    """Test cases for Risk Analytics API endpoints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='api_user',
            email='api@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create minimal test data
        self.category = RiskCategory.objects.create(
            name='API Test Category',
            color='#6f42c1'
        )
        
        self.risk = Risk.objects.create(
            title='API Test Risk',
            description='Risk for API testing',
            category=self.category,
            impact=4,
            likelihood=2,
            risk_level='medium',
            status='assessed',
            risk_owner=self.user
        )
    
    def test_dashboard_endpoint(self):
        """Test comprehensive dashboard endpoint."""
        url = reverse('riskanalytics-dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Verify all dashboard sections are present
        expected_sections = [
            'risk_overview', 'action_overview', 'heat_map', 'trend_analysis',
            'progress_analysis', 'control_integration', 'executive_summary'
        ]
        
        for section in expected_sections:
            self.assertIn(section, data)
        
        # Verify metadata
        self.assertIn('generated_at', data)
        self.assertIn('dashboard_version', data)
    
    def test_risk_overview_endpoint(self):
        """Test risk overview statistics endpoint."""
        url = reverse('riskanalytics-risk-overview')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Verify expected data structure
        self.assertIn('total_risks', data)
        self.assertIn('active_risks', data)
        self.assertIn('risk_level_distribution', data)
        self.assertIn('status_distribution', data)
        self.assertIn('category_distribution', data)
        self.assertIn('generated_at', data)
        
        # Verify data accuracy
        self.assertEqual(data['total_risks'], 1)
        self.assertEqual(data['active_risks'], 1)
    
    def test_action_overview_endpoint(self):
        """Test risk action overview endpoint."""
        url = reverse('riskanalytics-action-overview')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Verify expected data structure
        self.assertIn('total_actions', data)
        self.assertIn('active_actions', data)
        self.assertIn('completion_rate', data)
        self.assertIn('status_distribution', data)
        self.assertIn('priority_distribution', data)
        self.assertIn('top_assignees', data)
        self.assertIn('generated_at', data)
    
    def test_heat_map_endpoint(self):
        """Test risk heat map endpoint."""
        url = reverse('riskanalytics-heat-map')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Verify expected data structure
        self.assertIn('matrix_size', data)
        self.assertIn('total_risks', data)
        self.assertIn('heat_map', data)
        self.assertIn('impact_labels', data)
        self.assertIn('likelihood_labels', data)
        self.assertIn('generated_at', data)
        
        # Verify matrix structure
        heat_map = data['heat_map']
        self.assertIsInstance(heat_map, dict)
    
    def test_trends_endpoint(self):
        """Test risk trends analysis endpoint."""
        url = reverse('riskanalytics-trends')
        
        # Test default parameters
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(data['period_days'], 90)  # Default
        self.assertIn('creation_trend', data)
        self.assertIn('closure_trend', data)
        self.assertIn('active_trend', data)
        
        # Test custom days parameter
        response = self.client.get(url, {'days': 180})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['period_days'], 180)
        
        # Test invalid days parameter
        response = self.client.get(url, {'days': 'invalid'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test days parameter clamping
        response = self.client.get(url, {'days': 500})  # Above max
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['period_days'], 365)  # Clamped to max
    
    def test_action_progress_endpoint(self):
        """Test action progress analysis endpoint."""
        url = reverse('riskanalytics-action-progress')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Verify expected data structure
        self.assertIn('action_velocity', data)
        self.assertIn('actions_by_risk_level', data)
        self.assertIn('evidence_statistics', data)
        self.assertIn('treatment_effectiveness', data)
        self.assertIn('generated_at', data)
    
    def test_executive_summary_endpoint(self):
        """Test executive summary endpoint."""
        url = reverse('riskanalytics-executive-summary')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Verify expected data structure
        self.assertIn('risk_metrics', data)
        self.assertIn('quarterly_trend', data)
        self.assertIn('treatment_progress', data)
        self.assertIn('top_risk_areas', data)
        self.assertIn('governance_indicators', data)
        self.assertIn('report_period', data)
        self.assertIn('generated_at', data)
    
    def test_control_integration_endpoint(self):
        """Test control integration analysis endpoint."""
        url = reverse('riskanalytics-control-integration')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Verify expected data structure
        self.assertIn('risks_with_controls', data)
        self.assertIn('risks_without_controls', data)
        self.assertIn('control_coverage_rate', data)
        self.assertIn('category_control_analysis', data)
        self.assertIn('integration_status', data)
        self.assertIn('generated_at', data)
    
    def test_category_analysis_endpoint(self):
        """Test category analysis endpoint."""
        url = reverse('riskanalytics-category-analysis')
        
        # Test all categories analysis
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(data['category_name'], 'All Categories')
        self.assertIsNone(data['category_id'])
        
        # Test specific category analysis
        response = self.client.get(url, {'category_id': self.category.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(data['category_name'], 'API Test Category')
        self.assertEqual(data['category_id'], self.category.id)
        
        # Test invalid category ID
        response = self.client.get(url, {'category_id': 'invalid'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_authentication_required(self):
        """Test that authentication is required for analytics endpoints."""
        # Remove authentication
        self.client.force_authenticate(user=None)
        
        # Test various endpoints
        endpoints = [
            reverse('riskanalytics-dashboard'),
            reverse('riskanalytics-risk-overview'),
            reverse('riskanalytics-action-overview'),
            reverse('riskanalytics-heat-map'),
            reverse('riskanalytics-trends'),
            reverse('riskanalytics-executive-summary'),
        ]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RiskAnalyticsErrorHandlingTest(TestCase):
    """Test error handling in analytics functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='error_test_user',
            email='error@example.com',
            password='testpass123'
        )
    
    def test_empty_database_handling(self):
        """Test analytics with no data."""
        # Test with completely empty database
        overview = RiskAnalyticsService.get_risk_overview_stats()
        
        self.assertEqual(overview['total_risks'], 0)
        self.assertEqual(overview['active_risks'], 0)
        self.assertEqual(overview['average_risk_score'], 0)
        self.assertIsInstance(overview['risk_level_distribution'], dict)
        self.assertIsInstance(overview['category_distribution'], list)
    
    def test_heat_map_with_no_matrix(self):
        """Test heat map generation with no risk matrix."""
        # Ensure no risk matrices exist
        RiskMatrix.objects.all().delete()
        
        heat_map = RiskAnalyticsService.get_risk_heat_map_data()
        
        # Should default to 5x5 matrix
        self.assertEqual(heat_map['matrix_size'], 5)
        self.assertEqual(heat_map['total_risks'], 0)
        self.assertIsInstance(heat_map['heat_map'], dict)
    
    def test_trend_analysis_edge_cases(self):
        """Test trend analysis with edge cases."""
        # Test minimum days
        trends = RiskAnalyticsService.get_risk_trend_analysis(days=1)
        self.assertEqual(trends['period_days'], 1)
        
        # Test very large number of days
        trends = RiskAnalyticsService.get_risk_trend_analysis(days=1000)
        self.assertEqual(trends['period_days'], 1000)
        
        # Verify data structures are still valid
        self.assertIsInstance(trends['creation_trend'], list)
        self.assertIsInstance(trends['closure_trend'], list)
        self.assertIsInstance(trends['active_trend'], list)
    
    def test_admin_dashboard_error_handling(self):
        """Test admin dashboard error handling."""
        from ..admin import RiskAnalyticsDashboard
        
        # Test with no data
        data = RiskAnalyticsDashboard.get_admin_dashboard_data()
        
        # Should return safe defaults
        expected_keys = [
            'total_risks', 'active_risks', 'critical_high_risks', 'overdue_reviews',
            'total_actions', 'overdue_actions', 'completion_rate', 'avg_risk_score'
        ]
        
        for key in expected_keys:
            self.assertIn(key, data)
            self.assertIsInstance(data[key], (int, float))
        
        # Test HTML generation
        html = RiskAnalyticsDashboard.admin_dashboard_html()
        self.assertIn('Risk Analytics Dashboard', html)
        self.assertIn('Risk Overview', html)
        self.assertIn('Action Progress', html)


class RiskAnalyticsIntegrationTest(TestCase):
    """Integration tests for analytics with various scenarios."""
    
    def setUp(self):
        self.create_comprehensive_test_data()
    
    def create_comprehensive_test_data(self):
        """Create comprehensive test data for integration testing."""
        # Users
        self.users = []
        for i in range(5):
            user = User.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@example.com',
                first_name=f'User',
                last_name=f'{i}',
                password='testpass123'
            )
            self.users.append(user)
        
        # Categories
        self.categories = [
            RiskCategory.objects.create(name='Security', color='#dc3545'),
            RiskCategory.objects.create(name='Compliance', color='#fd7e14'),
            RiskCategory.objects.create(name='Operational', color='#28a745'),
            RiskCategory.objects.create(name='Financial', color='#6f42c1'),
        ]
        
        # Create risks across categories and levels
        risk_configs = [
            {'level': 'critical', 'count': 2, 'status': 'assessed'},
            {'level': 'high', 'count': 5, 'status': 'treatment_planned'},
            {'level': 'medium', 'count': 10, 'status': 'mitigated'},
            {'level': 'low', 'count': 8, 'status': 'accepted'},
        ]
        
        self.risks = []
        for config in risk_configs:
            for i in range(config['count']):
                impact = 5 if config['level'] == 'critical' else (4 if config['level'] == 'high' else 3)
                likelihood = 4 if config['level'] == 'critical' else (3 if config['level'] == 'high' else 2)
                
                risk = Risk.objects.create(
                    title=f"{config['level'].title()} Risk {i+1}",
                    description=f"Test {config['level']} risk for analytics",
                    category=self.categories[i % len(self.categories)],
                    impact=impact,
                    likelihood=likelihood,
                    risk_level=config['level'],
                    status=config['status'],
                    risk_owner=self.users[i % len(self.users)],
                    identified_date=date.today() - timedelta(days=i*10)
                )
                self.risks.append(risk)
        
        # Create actions for risks
        for i, risk in enumerate(self.risks[:15]):  # Create actions for first 15 risks
            RiskAction.objects.create(
                risk=risk,
                title=f'Action for {risk.title}',
                description=f'Treatment action for {risk.title}',
                action_type='mitigation',
                priority=risk.risk_level,
                assigned_to=self.users[i % len(self.users)],
                status=['pending', 'in_progress', 'completed'][i % 3],
                progress_percentage=[0, 50, 100][i % 3],
                due_date=date.today() + timedelta(days=(i-5)*5),  # Some overdue, some due soon
                start_date=date.today() - timedelta(days=30)
            )
    
    def test_comprehensive_analytics_performance(self):
        """Test analytics performance with realistic data volume."""
        import time
        
        # Test performance of all analytics methods
        start_time = time.time()
        overview = RiskAnalyticsService.get_risk_overview_stats()
        overview_time = time.time() - start_time
        
        start_time = time.time()
        dashboard = RiskReportGenerator.generate_risk_dashboard_data()
        dashboard_time = time.time() - start_time
        
        # Performance assertions (should complete quickly)
        self.assertLess(overview_time, 1.0)  # Should complete in under 1 second
        self.assertLess(dashboard_time, 3.0)  # Dashboard should complete in under 3 seconds
        
        # Data accuracy assertions
        self.assertEqual(overview['total_risks'], 25)
        self.assertGreater(overview['average_risk_score'], 0)
        
        # Verify dashboard completeness
        self.assertIn('risk_overview', dashboard)
        self.assertIn('heat_map', dashboard)
        self.assertIn('executive_summary', dashboard)
    
    def test_analytics_data_consistency(self):
        """Test data consistency across different analytics methods."""
        overview = RiskAnalyticsService.get_risk_overview_stats()
        executive = RiskAnalyticsService.get_executive_risk_summary()
        heat_map = RiskAnalyticsService.get_risk_heat_map_data()
        
        # Cross-validate total risks
        self.assertEqual(overview['total_risks'], executive['risk_metrics']['total_risks'])
        self.assertEqual(overview['active_risks'], executive['risk_metrics']['active_risks'])
        self.assertEqual(overview['active_risks'], heat_map['total_risks'])
        
        # Cross-validate risk levels
        overview_critical_high = (
            overview['risk_level_distribution'].get('critical', 0) +
            overview['risk_level_distribution'].get('high', 0)
        )
        self.assertEqual(overview_critical_high, executive['risk_metrics']['critical_high_risks'])
    
    def test_category_analysis_accuracy(self):
        """Test category analysis accuracy."""
        # Test each category individually
        for category in self.categories:
            category_analysis = RiskReportGenerator.get_risk_category_deep_dive(category.id)
            
            # Verify category-specific counts
            expected_count = Risk.objects.filter(category=category).count()
            self.assertEqual(category_analysis['risk_metrics']['total_risks'], expected_count)
            
            # Verify category name
            self.assertEqual(category_analysis['category_name'], category.name)
        
        # Test all categories combined
        all_analysis = RiskReportGenerator.get_risk_category_deep_dive(category_id=None)
        self.assertEqual(all_analysis['category_name'], 'All Categories')
        self.assertEqual(all_analysis['risk_metrics']['total_risks'], 25)