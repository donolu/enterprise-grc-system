from datetime import date, datetime
from types import SimpleNamespace

from exports.pdf_renderers import AssessmentSummaryPDFRenderer, ReportPDFRenderer


class EvidenceLinks:
    def __init__(self, count):
        self._count = count

    def count(self):
        return self._count


class RelatedLinks:
    def __init__(self, links=()):
        self._links = list(links)

    def all(self):
        return self._links


def test_assessment_summary_renderer_returns_pdf():
    user = SimpleNamespace(username="owner", get_full_name=lambda: "Report Owner")
    control = SimpleNamespace(control_id="AC-1", name="Access control")
    assessment = SimpleNamespace(
        control=control,
        status="in_progress",
        get_status_display=lambda: "In progress",
        assigned_to=user,
        due_date=date.today(),
        evidence_links=EvidenceLinks(2),
    )
    report = SimpleNamespace(
        title="Assessment summary",
        requested_by=user,
        include_overdue_items=True,
    )
    context = {
        "report": report,
        "framework": SimpleNamespace(name="ISO 27001", short_name="ISO27001"),
        "generated_at": datetime(2026, 8, 5, 10, 30),
        "completion_percentage": 50.0,
        "total_assessments": 2,
        "completed_assessments": 1,
        "overdue_assessments": 0,
        "evidence_stats": {"total_evidence": 2, "primary_evidence": 1},
        "assessments": [assessment],
    }

    pdf = AssessmentSummaryPDFRenderer().render(context)

    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000


def test_report_renderer_supports_all_remaining_report_types():
    user = SimpleNamespace(username="owner", get_full_name=lambda: "Report Owner")
    control = SimpleNamespace(control_id="AC-1", name="Access control", description="Description")
    assigned = SimpleNamespace(username="assignee", get_full_name=lambda: "Assignee")
    assessment = SimpleNamespace(
        control=control,
        status="not_started",
        get_status_display=lambda: "Not started",
        get_implementation_status_display=lambda: "Not implemented",
        assigned_to=assigned,
        due_date=date.today(),
        implementation_approach="Document the control.",
        evidence_links=RelatedLinks(),
    )
    report = SimpleNamespace(
        title="Report",
        requested_by=user,
        include_implementation_notes=True,
        include_evidence_summary=True,
    )
    common = {"report": report, "generated_at": datetime(2026, 8, 5, 10, 30)}
    renderer = ReportPDFRenderer()

    contexts = {
        "detailed_assessment": {**common, "assessments": [assessment]},
        "evidence_portfolio": {**common, "evidence_summary": []},
        "compliance_gap": {
            **common,
            "framework": SimpleNamespace(name="ISO 27001"),
            "total_gaps": 1,
            "not_started": [assessment],
            "in_progress_overdue": [],
            "missing_evidence": [],
            "no_primary_evidence": [],
        },
        "risk_analytics": {
            **common,
            "risk_analytics": {
                "overview": {"total_risks": 1, "risk_level_distribution": {"high": 1}},
                "actions": {"total_actions": 1, "completed_actions": 0},
            },
        },
    }

    for report_type, context in contexts.items():
        pdf = renderer.render(report_type, context)
        assert pdf.startswith(b"%PDF-"), report_type
        assert len(pdf) > 500, report_type
