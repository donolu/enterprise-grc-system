from __future__ import annotations

import io
from datetime import date, datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


class AssessmentSummaryPDFRenderer:
    """Render assessment summaries without an HTML/CSS runtime."""

    def render(self, context: dict[str, Any]) -> bytes:
        buffer = io.BytesIO()
        document = BaseDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            title=str(context["report"].title),
        )
        frame = Frame(document.leftMargin, document.bottomMargin, document.width, document.height)
        document.addPageTemplates(
            [PageTemplate(id="assessment-summary", frames=[frame], onPage=self._draw_footer)]
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle", parent=styles["Title"], fontSize=20, leading=24, textColor="#0066CC"
        )
        subtitle_style = ParagraphStyle(
            "ReportSubtitle", parent=styles["Normal"], fontSize=10, leading=14, textColor="#666666"
        )
        heading_style = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontSize=14,
            leading=18,
            textColor="#0066CC",
        )
        body_style = ParagraphStyle(
            "ReportBody", parent=styles["BodyText"], fontSize=9, leading=12, textColor="#333333"
        )
        cell_style = ParagraphStyle(
            "TableCell", parent=body_style, fontSize=7.5, leading=9, wordWrap="CJK"
        )
        cell_header_style = ParagraphStyle(
            "TableHeader", parent=cell_style, fontName="Helvetica-Bold", textColor=colors.white
        )
        metric_style = ParagraphStyle(
            "Metric",
            parent=body_style,
            alignment=TA_CENTER,
            fontSize=16,
            leading=19,
            textColor="#0066CC",
        )
        metric_label_style = ParagraphStyle(
            "MetricLabel", parent=body_style, alignment=TA_CENTER, fontSize=7.5, leading=9
        )

        report = context["report"]
        framework = context.get("framework")
        requested_by = report.requested_by.get_full_name() or report.requested_by.username
        story = [Paragraph(str(report.title), title_style)]
        framework_line = (
            f"Framework: {framework.name} ({framework.short_name})"
            if framework
            else "Assessment Summary Report"
        )
        story.extend(
            [
                Paragraph(framework_line, subtitle_style),
                Paragraph(
                    f"Generated: {self._format_datetime(context.get('generated_at'))}",
                    subtitle_style,
                ),
                Paragraph(f"Requested by: {requested_by}", subtitle_style),
                Spacer(1, 0.7 * cm),
            ]
        )

        if framework:
            story.append(Paragraph("Executive Summary", heading_style))
            evidence_stats = context.get("evidence_stats") or {}
            metrics = [
                (f"{context.get('completion_percentage', 0)}%", "Overall Completion"),
                (context.get("total_assessments", 0), "Total Assessments"),
                (context.get("completed_assessments", 0), "Completed"),
                (context.get("overdue_assessments", 0), "Overdue"),
                (evidence_stats.get("total_evidence", 0), "Evidence Items"),
                (evidence_stats.get("primary_evidence", 0), "Primary Evidence"),
            ]
            metric_rows = []
            for index in range(0, len(metrics), 3):
                metric_rows.append(
                    [
                        [Paragraph(str(value), metric_style), Paragraph(label, metric_label_style)]
                        for value, label in metrics[index : index + 3]
                    ]
                )
            metric_table = Table(metric_rows, colWidths=[document.width / 3] * 3)
            metric_table.setStyle(
                TableStyle(
                    [
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
                        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#EEEEEE")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            story.extend([metric_table, Spacer(1, 0.6 * cm)])

        story.append(Paragraph("Assessment Status Breakdown", heading_style))
        story.append(
            self._assessment_table(context.get("assessments", []), cell_style, cell_header_style)
        )

        if report.include_overdue_items and context.get("overdue_assessments", 0) > 0:
            story.extend(
                [
                    Spacer(1, 0.6 * cm),
                    Paragraph("Overdue Items Requiring Attention", heading_style),
                    Paragraph("The following assessments require immediate attention:", body_style),
                    self._overdue_table(
                        context.get("assessments", []), cell_style, cell_header_style
                    ),
                ]
            )

        document.build(story)
        return buffer.getvalue()

    @staticmethod
    def _assessment_table(assessments, cell_style, header_style):
        headers = ["Control ID", "Control Title", "Status", "Assigned To", "Due Date", "Evidence"]
        rows = [[Paragraph(value, header_style) for value in headers]]
        for assessment in assessments:
            assigned_to = assessment.assigned_to
            assigned_name = (
                (assigned_to.get_full_name() or assigned_to.username)
                if assigned_to
                else "Unassigned"
            )
            rows.append(
                [
                    Paragraph(str(assessment.control.control_id), cell_style),
                    Paragraph(str(assessment.control.name), cell_style),
                    Paragraph(str(assessment.get_status_display()), cell_style),
                    Paragraph(assigned_name, cell_style),
                    Paragraph(
                        assessment.due_date.isoformat() if assessment.due_date else "Not set",
                        cell_style,
                    ),
                    Paragraph(str(assessment.evidence_links.count()), cell_style),
                ]
            )
        table = Table(
            rows,
            repeatRows=1,
            colWidths=[1.7 * cm, 5.2 * cm, 2.2 * cm, 3.1 * cm, 2.3 * cm, 1.4 * cm],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0066CC")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#F5F5F5")],
                    ),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return table

    @staticmethod
    def _overdue_table(assessments, cell_style, header_style):
        headers = ["Control ID", "Control Title", "Assigned To", "Due Date"]
        rows = [[Paragraph(value, header_style) for value in headers]]
        for assessment in assessments:
            if (
                assessment.status == "complete"
                or not assessment.due_date
                or assessment.due_date >= date.today()
            ):
                continue
            assigned_to = assessment.assigned_to
            assigned_name = (
                (assigned_to.get_full_name() or assigned_to.username)
                if assigned_to
                else "Unassigned"
            )
            rows.append(
                [
                    Paragraph(str(assessment.control.control_id), cell_style),
                    Paragraph(str(assessment.control.name), cell_style),
                    Paragraph(assigned_name, cell_style),
                    Paragraph(assessment.due_date.isoformat(), cell_style),
                ]
            )
        table = Table(rows, repeatRows=1, colWidths=[2.5 * cm, 8.5 * cm, 4 * cm, 2.5 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0066CC")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        return table

    @staticmethod
    def _format_datetime(value: datetime | None) -> str:
        return value.strftime("%B %d, %Y %I:%M %p") if value else "Unknown"

    @staticmethod
    def _draw_footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawCentredString(A4[0] / 2, 1.1 * cm, f"Page {document.page}")
        canvas.restoreState()
