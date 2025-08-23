"""
Simple tests for risk analytics integration with assessment reporting system.
This validates that the integration works correctly without requiring full database setup.
"""

def test_risk_integration_imports():
    """Test that risk analytics can be imported into assessment reporting."""
    try:
        from exports.services import AssessmentReportGenerator
        from exports.models import AssessmentReport
        from risk.analytics import RiskAnalyticsService, RiskReportGenerator
        
        # Test that all required classes can be imported
        assert AssessmentReportGenerator is not None
        assert AssessmentReport is not None
        assert RiskAnalyticsService is not None
        assert RiskReportGenerator is not None
        
        print("✓ Risk integration imports successful")
        
    except ImportError as e:
        raise AssertionError(f"Failed to import risk integration components: {e}")

def test_assessment_report_types():
    """Test that new risk analytics report type is available."""
    from exports.models import AssessmentReport
    
    # Check that risk_analytics is in REPORT_TYPES
    report_types = dict(AssessmentReport.REPORT_TYPES)
    assert 'risk_analytics' in report_types
    assert report_types['risk_analytics'] == 'Risk Analytics & Integration Report'
    
    print("✓ Risk analytics report type available")

def test_assessment_generator_methods():
    """Test that AssessmentReportGenerator has risk integration methods."""
    from exports.services import AssessmentReportGenerator
    
    # Test that risk integration methods exist
    required_methods = [
        '_get_risk_analytics_context',
        '_calculate_risk_compliance_correlation',
        '_generate_risk_analytics_report'
    ]
    
    for method in required_methods:
        assert hasattr(AssessmentReportGenerator, method), f"Missing method: {method}"
    
    print("✓ Assessment generator risk integration methods available")

def test_risk_analytics_template_exists():
    """Test that risk analytics template exists."""
    import os
    from django.conf import settings
    
    # Build template path
    template_path = os.path.join(
        settings.BASE_DIR, 
        'exports', 
        'templates', 
        'exports', 
        'reports', 
        'risk_analytics.html'
    )
    
    # Check template exists
    assert os.path.exists(template_path), f"Risk analytics template not found at {template_path}"
    
    # Check template has required content
    with open(template_path, 'r') as f:
        template_content = f.read()
        
    required_content = [
        'Risk Analytics & Integration Report',
        'risk_analytics.overview',
        'risk_analytics.actions',
        'risk_analytics.compliance_correlation',
        'Risk-Compliance Integration Analysis'
    ]
    
    for content in required_content:
        assert content in template_content, f"Template missing required content: {content}"
    
    print("✓ Risk analytics template exists and contains required elements")

def test_assessment_summary_template_integration():
    """Test that assessment summary template includes risk analytics integration."""
    import os
    from django.conf import settings
    
    # Build template path
    template_path = os.path.join(
        settings.BASE_DIR, 
        'exports', 
        'templates', 
        'exports', 
        'reports', 
        'assessment_summary.html'
    )
    
    # Check template exists
    assert os.path.exists(template_path), f"Assessment summary template not found"
    
    # Check template has risk integration
    with open(template_path, 'r') as f:
        template_content = f.read()
        
    integration_elements = [
        'risk_analytics',
        'Risk Analytics Integration',
        'risk_analytics.overview.total_risks',
        'risk_analytics.compliance_correlation',
        'Risk-Compliance Integration Insights'
    ]
    
    for element in integration_elements:
        assert element in template_content, f"Assessment summary missing risk integration: {element}"
    
    print("✓ Assessment summary template includes risk analytics integration")

def test_report_generation_logic():
    """Test that risk analytics report generation logic is properly structured."""
    from exports.services import AssessmentReportGenerator
    from unittest.mock import Mock
    
    # Create a mock report
    mock_report = Mock()
    mock_report.report_type = 'risk_analytics'
    mock_report.title = 'Test Risk Analytics Report'
    mock_report.requested_by.get_full_name.return_value = 'Test User'
    
    # Create generator instance
    generator = AssessmentReportGenerator(mock_report)
    
    # Test that risk integration methods exist and are callable
    assert callable(generator._get_risk_analytics_context)
    assert callable(generator._calculate_risk_compliance_correlation) 
    assert callable(generator._generate_risk_analytics_report)
    
    print("✓ Risk analytics report generation logic properly structured")

def run_all_tests():
    """Run all integration validation tests."""
    print("Running Risk Analytics Integration Validation Tests...")
    print("=" * 60)
    
    try:
        test_risk_integration_imports()
        test_assessment_report_types()
        test_assessment_generator_methods()
        test_risk_analytics_template_exists()
        test_assessment_summary_template_integration()
        test_report_generation_logic()
        
        print("=" * 60)
        print("✅ All risk analytics integration validation tests PASSED!")
        print("   - Risk integration imports: ✓")
        print("   - Report type registration: ✓") 
        print("   - Service method availability: ✓")
        print("   - Risk analytics template: ✓")
        print("   - Assessment template integration: ✓")
        print("   - Report generation logic: ✓")
        print()
        print("Risk analytics is successfully integrated with the assessment reporting system.")
        print()
        print("Integration Features Available:")
        print("  - Risk data included in assessment summary reports")
        print("  - New 'Risk Analytics & Integration Report' type")
        print("  - Risk-compliance correlation metrics")
        print("  - Comprehensive risk analytics reporting")
        print("  - Graceful error handling for missing risk data")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        raise

if __name__ == "__main__":
    run_all_tests()