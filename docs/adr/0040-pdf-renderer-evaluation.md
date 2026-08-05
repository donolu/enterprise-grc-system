# ADR-0040: PDF Renderer Evaluation

- Status: Proposed
- Date: 2026-08-05
- Decision scope: assessment report generation

## Context

The platform currently uses WeasyPrint to render all assessment-report HTML templates. This preserves CSS well, but it adds native Cairo/Pango dependencies to the production image and is subject to the presentational-hints advisory tracked in issue #129. The application already declares ReportLab and its assessment reports are structured documents containing headings, metrics and tables.

## Decision

Prototype ReportLab for the assessment-summary report first. The prototype renders the report title and metadata, executive metrics, assessment table, overdue table and page numbers without an HTML/CSS runtime.

Keep WeasyPrint for the other report types during the evaluation. Removing it before parity has been demonstrated would create a regression risk for detailed assessment, evidence portfolio, compliance-gap and risk-analytics reports.

## Rationale

ReportLab is a better operational fit for structured compliance reports:

- no browser process or additional rendering service;
- no Cairo/Pango runtime dependency;
- deterministic pagination for tables;
- already present in the Python dependency set.

Playwright/Chromium remains a possible alternative if visual parity with the existing HTML templates becomes more important than image size and runtime complexity. It should be evaluated separately rather than introduced alongside this prototype.

## Consequences

- The assessment-summary path now has an independent renderer that can be tested without WeasyPrint.
- The remaining report types still require WeasyPrint and the existing presentational_hints=False mitigation.
- A follow-up migration slice must compare generated PDFs for content, pagination and styling before the dependency can be removed.
