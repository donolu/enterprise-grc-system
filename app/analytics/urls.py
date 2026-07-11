"""
Analytics API URL Configuration

URL patterns for analytics and reporting endpoints.
"""

from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # Dashboard endpoints
    path('executive/', views.executive_dashboard, name='executive_dashboard'),
    path('compliance/', views.compliance_dashboard, name='compliance_dashboard'),
    path('vendor-risk/', views.vendor_risk_dashboard, name='vendor_risk_dashboard'),
    path('policy-management/', views.policy_management_dashboard, name='policy_management_dashboard'),
    path('training-effectiveness/', views.training_effectiveness_dashboard, name='training_effectiveness_dashboard'),

    # Advanced analytics (premium features)
    path('integrated-risk-posture/', views.integrated_risk_posture, name='integrated_risk_posture'),
    path('executive-report/', views.executive_report_data, name='executive_report_data'),

    # Operational dashboards
    path('operational/', views.operational_dashboard, name='operational_dashboard'),

    # Export and reporting
    path('export/', views.export_report, name='export_report'),
    path('reports/', views.my_reports, name='my_reports'),
    path('reports/<uuid:report_id>/status/', views.report_status, name='report_status'),
    path('reports/<uuid:report_id>/download/', views.download_report, name='download_report'),
    path('reports/<uuid:report_id>/', views.delete_report, name='delete_report'),
    path('cache/refresh/', views.refresh_cache, name='refresh_cache'),

    # System health
    path('health/', views.analytics_health_check, name='analytics_health_check'),
]