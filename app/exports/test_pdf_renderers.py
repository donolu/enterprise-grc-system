from datetime import date, datetime
from types import SimpleNamespace

from exports.pdf_renderers import AssessmentSummaryPDFRenderer


class EvidenceLinks:
    def __init__(self, count):
        self._count = count

    def count(self):
        return self._count


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
