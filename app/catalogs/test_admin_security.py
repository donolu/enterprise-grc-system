from types import SimpleNamespace

from django.contrib.admin.sites import AdminSite

from catalogs.admin import ControlAssessmentAdmin
from catalogs.models import ControlAssessment


def test_change_log_display_escapes_entry_values():
    admin = ControlAssessmentAdmin(ControlAssessment, AdminSite())
    obj = SimpleNamespace(
        change_log=[
            {
                "user": "<script>alert(1)</script>",
                "timestamp": "2026-07-29T22:00:00Z",
                "description": "<img src=x onerror=alert(1)>",
            }
        ]
    )

    rendered = str(admin.change_log_display(obj))

    assert "<script>" not in rendered
    assert "<img" not in rendered
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered
    assert "&lt;img src=x onerror=alert(1)&gt;" in rendered
