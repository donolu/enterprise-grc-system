"""Service-boundary regression tests for cross-module analytics."""

import ast
from pathlib import Path

import pytest

from analytics.services import CrossModuleAnalyticsService


FORBIDDEN_DIRECT_MODEL_IMPORTS = {
    "catalogs.models",
    "policies.models",
    "risk.models",
    "training.models",
    "vendors.models",
}


def test_analytics_services_do_not_import_cross_domain_models_directly():
    source = Path(__file__).with_name("services.py").read_text()
    tree = ast.parse(source)

    direct_model_imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module in FORBIDDEN_DIRECT_MODEL_IMPORTS
    }

    assert direct_model_imports == set()


@pytest.mark.django_db
def test_cross_module_dashboard_services_smoke():
    assert "risk_summary" in CrossModuleAnalyticsService.get_executive_dashboard_data()
    assert "framework_statistics" in CrossModuleAnalyticsService.get_compliance_dashboard_data()
    assert "vendor_risk_statistics" in CrossModuleAnalyticsService.get_vendor_risk_dashboard_data()
    assert "policy_statistics" in CrossModuleAnalyticsService.get_policy_management_dashboard_data()
    assert "video_engagement" in CrossModuleAnalyticsService.get_training_effectiveness_dashboard_data()
    assert "risk_source_analysis" in CrossModuleAnalyticsService.get_integrated_risk_posture()
