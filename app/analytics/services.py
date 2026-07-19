"""
Cross-module analytics orchestration.

The analytics app composes domain-owned service outputs. It does not reach
directly into other apps' models; each domain owns its own ORM queries.
"""

from datetime import timedelta

from django.utils import timezone

from catalogs.services import CatalogueAnalyticsService
from policies.services import PolicyAnalyticsService
from risk.services import RiskDomainAnalyticsService
from training.services import TrainingAnalyticsService
from vendors.services import VendorAnalyticsService


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

        return {
            "risk_summary": RiskDomainAnalyticsService.executive_summary(now),
            "compliance_summary": CatalogueAnalyticsService.executive_summary(now),
            "policy_summary": PolicyAnalyticsService.executive_summary(),
            "vendor_summary": VendorAnalyticsService.executive_summary(now),
            "training_summary": TrainingAnalyticsService.executive_summary(),
            "generated_at": now.isoformat(),
            "report_period": {
                "start_date": quarter_ago.isoformat(),
                "end_date": now.isoformat(),
            },
        }

    @staticmethod
    def get_compliance_dashboard_data():
        """
        Get comprehensive compliance dashboard metrics and trends.

        Returns:
            dict: Compliance-focused analytics
        """
        return CatalogueAnalyticsService.dashboard_data(timezone.now().date())

    @staticmethod
    def get_vendor_risk_dashboard_data():
        """
        Get vendor management and risk assessment dashboard data.

        Returns:
            dict: Vendor-focused analytics and risk metrics
        """
        return VendorAnalyticsService.dashboard_data(timezone.now().date())

    @staticmethod
    def get_policy_management_dashboard_data():
        """
        Get policy management and acknowledgment tracking dashboard data.

        Returns:
            dict: Policy-focused analytics and compliance metrics
        """
        return PolicyAnalyticsService.dashboard_data(timezone.now().date())

    @staticmethod
    def get_training_effectiveness_dashboard_data():
        """
        Get training program effectiveness and engagement analytics.

        Returns:
            dict: Training-focused metrics and engagement analysis
        """
        return TrainingAnalyticsService.dashboard_data(timezone.now().date())

    @staticmethod
    def get_integrated_risk_posture():
        """
        Get integrated risk posture across all modules for executive reporting.

        Returns:
            dict: Cross-module risk analysis and correlations
        """
        now = timezone.now().date()
        risk_velocity = RiskDomainAnalyticsService.velocity_metrics(now)
        risk_velocity["overdue_items"] = (
            risk_velocity.pop("overdue_actions")
            + CatalogueAnalyticsService.overdue_assessment_count(now)
            + VendorAnalyticsService.overdue_task_count(now)
        )

        risk_sources = {
            "operational_risks": RiskDomainAnalyticsService.active_risk_count(),
            "compliance_gaps": CatalogueAnalyticsService.compliance_gap_count(),
            "vendor_risks": VendorAnalyticsService.high_or_critical_vendor_count(),
            "policy_violations": PolicyAnalyticsService.policy_violation_count(),
            "training_gaps": TrainingAnalyticsService.training_gap_count(),
        }

        framework_risk_correlation = CatalogueAnalyticsService.framework_risk_correlation(now)
        for framework in framework_risk_correlation:
            # Risk-control mappings are not modelled yet; preserve the response key
            # while keeping the catalogue service as the source of framework metrics.
            framework["related_risks"] = 0

        return {
            "risk_source_analysis": risk_sources,
            "vendor_risk_correlation": VendorAnalyticsService.high_risk_assessment_correlation(),
            "framework_risk_correlation": framework_risk_correlation,
            "risk_velocity_metrics": risk_velocity,
            "risk_maturity_indicators": {
                "treatment_coverage": round(
                    RiskDomainAnalyticsService.treatment_coverage_percentage(), 1
                ),
                "automation_rate": round(
                    CatalogueAnalyticsService.automation_rate_percentage(), 1
                ),
                "acknowledgment_rate": round(
                    PolicyAnalyticsService.acknowledgment_rate_percentage(), 1
                ),
                "assessment_coverage": round(
                    VendorAnalyticsService.assessment_coverage_percentage(), 1
                ),
            },
            "overall_risk_score": round(sum(risk_sources.values()) / len(risk_sources), 1),
            "generated_at": now.isoformat(),
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
            "executive_dashboard": CrossModuleAnalyticsService.get_executive_dashboard_data(),
            "integrated_risk_posture": CrossModuleAnalyticsService.get_integrated_risk_posture(),
            "compliance_overview": CrossModuleAnalyticsService.get_compliance_dashboard_data(),
            "vendor_risk_summary": CrossModuleAnalyticsService.get_vendor_risk_dashboard_data(),
            "policy_compliance": CrossModuleAnalyticsService.get_policy_management_dashboard_data(),
            "training_effectiveness": (
                CrossModuleAnalyticsService.get_training_effectiveness_dashboard_data()
            ),
            "report_metadata": {
                "generated_at": timezone.now().isoformat(),
                "report_type": "executive_comprehensive",
                "version": "1.0",
            },
        }

    @staticmethod
    def generate_operational_dashboard_data():
        """
        Generate operational dashboard data for day-to-day management.

        Returns:
            dict: Operational analytics focused on actionable metrics
        """
        return {
            "risk_analytics": RiskDomainAnalyticsService.overview_stats(),
            "compliance_metrics": CrossModuleAnalyticsService.get_compliance_dashboard_data(),
            "vendor_management": CrossModuleAnalyticsService.get_vendor_risk_dashboard_data(),
            "policy_tracking": CrossModuleAnalyticsService.get_policy_management_dashboard_data(),
            "training_progress": (
                CrossModuleAnalyticsService.get_training_effectiveness_dashboard_data()
            ),
            "report_metadata": {
                "generated_at": timezone.now().isoformat(),
                "report_type": "operational_dashboard",
                "version": "1.0",
            },
        }
