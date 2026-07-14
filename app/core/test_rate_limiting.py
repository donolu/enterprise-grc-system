"""API rate-limit configuration regression tests."""

from rest_framework.settings import api_settings
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle

from authn.views import (
    ApprovePushChallengeView,
    ConfirmTOTPView,
    EnableTwoFactorView,
    LoginView,
    RegisterPushDeviceView,
    RegisterView,
    SetupTOTPView,
    VerifyOTPView,
)
from catalogs.views import ControlAssessmentViewSet, ControlEvidenceViewSet
from core.views import DocumentViewSet
from exports.views import AssessmentReportViewSet


def test_default_drf_throttles_are_enabled():
    throttle_classes = set(api_settings.DEFAULT_THROTTLE_CLASSES)

    assert {AnonRateThrottle, UserRateThrottle, ScopedRateThrottle}.issubset(
        throttle_classes
    )
    assert {"anon", "user", "auth", "two_factor", "exports", "evidence_upload"} <= set(
        api_settings.DEFAULT_THROTTLE_RATES
    )


def test_auth_and_two_factor_views_have_sensitive_scopes():
    assert RegisterView.throttle_scope == "auth"
    assert LoginView.throttle_scope == "auth"

    two_factor_views = [
        EnableTwoFactorView,
        VerifyOTPView,
        SetupTOTPView,
        ConfirmTOTPView,
        RegisterPushDeviceView,
        ApprovePushChallengeView,
    ]
    assert all(view.throttle_scope == "two_factor" for view in two_factor_views)


def test_export_views_use_export_scope():
    assert AssessmentReportViewSet.throttle_scope == "exports"


def test_upload_actions_use_evidence_upload_scope():
    assert DocumentViewSet.throttle_scope_by_action == {"create": "evidence_upload"}
    assert ControlEvidenceViewSet.throttle_scope_by_action == {
        "create": "evidence_upload"
    }
    assert ControlAssessmentViewSet.throttle_scope_by_action == {
        "upload_evidence": "evidence_upload",
        "bulk_upload_evidence": "evidence_upload",
    }
