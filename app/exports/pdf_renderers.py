from __future__ import annotations

import io
from datetime import date, datetime
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


class ReportPDFRenderer:
    """Render the remaining report types using ReportLab primitives."""

    _BLUE = colors.HexColor("#0066CC")
    _GREY = colors.HexColor("#666666")

    def render(self, report_type: str, context: dict[str, Any]) -> bytes:
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
            [PageTemplate(id="report", frames=[frame], onPage=self._draw_footer)]
        )
        styles = getSampleStyleSheet()
        body = ParagraphStyle("ReportBody", parent=styles["BodyText"], fontSize=9, leading=12)
        heading = ParagraphStyle(
            "ReportHeading", parent=styles["Heading2"], fontSize=14, leading=18, textColor=self._BLUE
        )
        title = ParagraphStyle(
            "ReportTitle", parent=styles["Title"], fontSize=20, leading=24, textColor=self._BLUE
        )
        cell = ParagraphStyle("ReportCell", parent=body, fontSize=7.5, leading=9)
        header = ParagraphStyle("ReportHeader", parent=cell, fontName="Helvetica-Bold", textColor=colors.white)

        report = context["report"]
        requested_by = report.requested_by.get_full_name() or report.requested_by.username
        story = [
            Paragraph(escape(str(report.title)), title),
            Paragraph(escape(self._subtitle(report_type, context)), body),
            Paragraph(f"Generated: {self._format_datetime(context.get('generated_at'))}", body),
            Paragraph(f"Requested by: {escape(str(requested_by))}", body),
            Spacer(1, 0.7 * cm),
        ]
        if report_type == "detailed_assessment":
            story.extend(self._detailed_assessment(context, heading, body, cell, header))
        elif report_type == "evidence_portfolio":
            story.extend(self._evidence_portfolio(context, heading, body, cell, header))
        elif report_type == "compliance_gap":
            story.extend(self._compliance_gap(context, heading, body, cell, header))
        elif report_type == "risk_analytics":
            story.extend(self._risk_analytics(context, heading, body, cell, header))
        else:
            raise ValueError(f"Unsupported ReportLab report type: {report_type}")
        document.build(story)
        return buffer.getvalue()

    def _detailed_assessment(self, context, heading, body, cell, header):
        story = []
        assessments = list(context.get("assessments", []))
        for index, assessment in enumerate(assessments):
            if index:
                story.append(PageBreak())
            story.append(Paragraph(escape(f"{assessment.control.control_id}: {assessment.control.name}"), heading))
            assigned = assessment.assigned_to
            assigned_name = (assigned.get_full_name() or assigned.username) if assigned else "Unassigned"
            details = [
                ["Status", assessment.get_status_display()],
                ["Assigned To", assigned_name],
                ["Due Date", assessment.due_date.isoformat() if assessment.due_date else "Not set"],
                ["Implementation Status", assessment.get_implementation_status_display()],
            ]
            story.append(self._key_value_table(details, cell))
            if assessment.control.description:
                story.extend([Paragraph("Control Description", heading), Paragraph(escape(str(assessment.control.description)), body)])
            report = context["report"]
            if report.include_implementation_notes and assessment.implementation_approach:
                approach = escape(str(assessment.implementation_approach)).replace("\n", "<br/>")
                story.extend([Paragraph("Implementation Approach", heading), Paragraph(approach, body)])
            if report.include_evidence_summary:
                links = list(assessment.evidence_links.all())
                story.append(Paragraph(f"Evidence Summary ({len(links)} items)", heading))
                rows = [["Evidence Title", "Type", "Purpose", "Primary", "Date"]]
                rows.extend([
                    [
                        link.evidence.title,
                        link.evidence.get_evidence_type_display(),
                        link.evidence_purpose or "General Evidence",
                        "Yes" if link.is_primary_evidence else "No",
                        link.evidence.evidence_date.isoformat() if link.evidence.evidence_date else "Not set",
                    ] for link in links
                ])
                story.append(self._table(rows, [4.0 * cm, 3.0 * cm, 5.0 * cm, 2.0 * cm, 2.5 * cm], cell, header))
        if not assessments:
            story.append(Paragraph("No assessments found for the specified criteria.", body))
        return story

    def _evidence_portfolio(self, context, heading, body, cell, header):
        summary = list(context.get("evidence_summary", []))
        story = [Paragraph("Evidence Overview", heading), Paragraph(f"Unique evidence items: {len(summary)}", body)]
        rows = [["Evidence Title", "Type", "Assessments", "Primary", "Validated"]]
        for info in summary:
            evidence = info["evidence"]
            rows.append([
                evidence.title,
                evidence.get_evidence_type_display(),
                str(len(info["assessments"])),
                str(info["is_primary_count"]),
                "Yes" if evidence.is_validated else "No",
            ])
        story.extend([Paragraph("Evidence Inventory", heading), self._table(rows, [5.0 * cm, 3.5 * cm, 3.0 * cm, 2.5 * cm, 2.5 * cm], cell, header)])
        if not summary:
            story.append(Paragraph("No evidence items found for the specified criteria.", body))
        return story

    def _compliance_gap(self, context, heading, body, cell, header):
        story = [Paragraph("Executive Summary", heading), Paragraph(f"Total compliance gaps: {context.get('total_gaps', 0)}", body)]
        for key, label in (("not_started", "Assessments Not Started"), ("in_progress_overdue", "In Progress but Overdue"), ("missing_evidence", "Completed but Missing Evidence"), ("no_primary_evidence", "Missing Primary Evidence Designation")):
            queryset = list(context.get(key, []))
            story.append(Paragraph(f"{label} ({len(queryset)})", heading))
            rows = [["Control ID", "Control Title", "Assigned To", "Due Date", "Status"]]
            for assessment in queryset:
                assigned = assessment.assigned_to
                rows.append([
                    assessment.control.control_id,
                    assessment.control.name,
                    (assigned.get_full_name() or assigned.username) if assigned else "Unassigned",
                    assessment.due_date.isoformat() if assessment.due_date else "Not set",
                    assessment.get_status_display(),
                ])
            story.append(self._table(rows, [2.5 * cm, 6.0 * cm, 4.0 * cm, 2.5 * cm, 2.5 * cm], cell, header))
        return story

    def _risk_analytics(self, context, heading, body, cell, header):
        analytics = context.get("risk_analytics", {})
        overview = analytics.get("overview", {})
        actions = analytics.get("actions", {})
        story = [Paragraph("Executive Risk Summary", heading)]
        rows = [["Metric", "Value"], ["Total Risks", overview.get("total_risks", 0)], ["Active Risks", overview.get("active_risks", 0)], ["Critical Risks", overview.get("critical_risks", 0)], ["High Risks", overview.get("high_risks", 0)], ["Mitigation Actions", actions.get("total_actions", 0)], ["Completed Actions", actions.get("completed_actions", 0)]]
        story.append(self._table(rows, [8 * cm, 8 * cm], cell, header))
        distribution = overview.get("risk_level_distribution", {})
        if distribution:
            story.extend([Paragraph("Risk Level Distribution", heading), self._table([["Level", "Count"], *[[str(k).title(), v] for k, v in distribution.items()]], [8 * cm, 8 * cm], cell, header)])
        return story

    @staticmethod
    def _key_value_table(rows, cell):
        return Table([[Paragraph(escape(str(k)), cell), Paragraph(escape(str(v)), cell)] for k, v in rows], colWidths=[4 * cm, 12 * cm], style=TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))

    @staticmethod
    def _table(rows, widths, cell, header):
        formatted = [[Paragraph(escape(str(value)), header if row_index == 0 else cell) for value in row] for row_index, row in enumerate(rows)]
        return Table(formatted, repeatRows=1, colWidths=widths, style=TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0066CC")), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))

    @staticmethod
    def _subtitle(report_type, context):
        framework = context.get("framework")
        label = report_type.replace("_", " ").title()
        return f"{label} - {framework.name}" if framework else label

    @staticmethod
    def _format_datetime(value):
        return value.strftime("%B %d, %Y %I:%M %p") if value else "Unknown"

    @staticmethod
    def _draw_footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawCentredString(A4[0] / 2, 1.1 * cm, f"Page {document.page}")
        canvas.restoreState()


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
