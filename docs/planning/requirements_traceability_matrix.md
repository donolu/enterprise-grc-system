# Requirements Traceability Matrix

This matrix maps the original GRC SaaS brief to current implementation status and delivery tickets.

Status values:

- **Done:** implemented and broadly aligned.
- **Partial:** foundation exists, but business requirement is not complete.
- **Missing:** no clear first-class implementation yet.
- **Tracked Elsewhere:** existing issue covers the work.

| ID | Requirement | Current Status | Evidence / Notes | Tracking |
| --- | --- | --- | --- | --- |
| RTM-001 | Multi-tenant client isolation | Done | `django-tenants`, tenant models and tenant isolation tests exist. | Existing architecture ADRs |
| RTM-002 | Email 2FA / MFA | Done | Email OTP and TOTP flows exist in `authn`. | Existing ADR-0003/0010 |
| RTM-003 | Free/basic/enterprise plans | Partial | Plans, subscriptions and limits exist. Module-level entitlements are not complete. | #135 |
| RTM-004 | One-month trial for one item/module | Missing | Trial fields exist, but one-module trial packaging is not enforced. | #135 |
| RTM-005 | ISO/NIST/PCI/control workflows | Partial | Generic Framework/Clause/Control/Assessment exists; content packs/imports incomplete. | #132 |
| RTM-006 | ISO 27001 source templates | Partial | Source ZIP includes ISO mandatory docs; not imported/linked. | #133 |
| RTM-007 | ISO 20000 / ISO 22301 / CIS / PSD2 / GDPR / future frameworks | Partial | Data model supports custom frameworks; source content not loaded. | #132 |
| RTM-008 | PCI guide/workflow | Partial | Source ZIP contains `PCI V4.0.xlsx`; import/linking not complete. | #132, #133 |
| RTM-009 | Templates/samples linked to controls/items | Missing | Document storage exists, but template linkage is not implemented as a product feature. | #133 |
| RTM-010 | Client document repository | Partial | Tenant-aware document model/storage exists. Repository lifecycle and finalized PDF-only flow incomplete. | #138 |
| RTM-011 | Upload existing external documents | Partial | Upload/storage exists; module-specific replacement workflow needs completion. | #133, #138 |
| RTM-012 | Inline Word/spreadsheet modification | Missing | No selected editing architecture. | #138 |
| RTM-013 | Final downloads only as PDF after modification | Missing | PDF/report generation exists, but controlled document finalization flow is missing. | #138, #129 |
| RTM-014 | Risk register with calculated rating | Done | Risk model calculates risk level from impact/likelihood. | Existing risk ADRs |
| RTM-015 | Risk owner overdue notifications | Partial | Risk actions/reminders exist; unified calendar/deadline hub still needed. | #136 |
| RTM-016 | Risk remediation evidence upload | Partial | Evidence/document models exist; module-specific linkage should be verified. | Existing evidence ADR, #139 |
| RTM-017 | Vendor management | Partial | Vendor app/models/docs exist; API route mounting issue logged. | #128 |
| RTM-018 | Vendor activity date checks/reminders | Partial | Vendor task architecture exists; route/usability validation needed. | #128, #136 |
| RTM-019 | Policy repository | Done | Policy/category/version/document models exist. | Existing ADR-0021 |
| RTM-020 | Policy acknowledgment tracking | Done | Acknowledgment/distribution/reminder tasks exist. | Existing ADR-0022 |
| RTM-021 | Security awareness email campaigns | Done | Training campaign models/tasks exist. | Existing ADR-0023 |
| RTM-022 | Synthesia/video training | Partial | Training video model supports Synthesia/custom URLs; content loading needed. | Future content work |
| RTM-023 | Knowledge base/how-to content | Missing | No clear first-class knowledge base module found. | #141 |
| RTM-024 | Calendar module | Missing | No unified calendar/event module found. | #136 |
| RTM-025 | Vulnerability scanning | Missing | Policies/controls mention scanning; scanner integration not implemented. | #137 |
| RTM-026 | User activity tracking | Partial | AuditEvent exists; coverage and UI/reporting should be validated. | #139 |
| RTM-027 | Product analytics for Axim | Partial | GRC analytics exist; operator/product usage metrics need explicit design. | #143 |
| RTM-028 | Client data exports in spreadsheet/PDF | Partial | Reporting/export modules exist; coverage and API reliability incomplete. | #130, #139 |
| RTM-029 | Asset register | Missing | Source ZIP includes asset register; no first-class module found. | #134 |
| RTM-030 | Regulatory and contractual sheet | Partial | Source ZIP includes legal/regulatory sheet; not imported as structured data. | #142 |
| RTM-031 | Non-conformity log, scope doc, metrics, agenda, management review | Partial | Source ZIP includes several ISO mandatory docs; structured workflows not complete. | #142 |
| RTM-032 | Azure deployment | Partial | Azure-oriented settings/storage exist; platform-agnostic hosting is also tracked. | #92 |
| RTM-033 | GitHub-based delivery | Done | GitHub CI/security workflows exist. | Existing CI issues |
| RTM-034 | ADR documentation | Partial | Many ADRs exist; programme-level BRD/TRD traceability added under #140. | #140 |

## Ordered Delivery Sequence

1. #132 - Import framework spreadsheets into reusable control catalogs.
2. #133 - Import and link Axim template library.
3. #128 - Mount or retire vendor management API routes.
4. #134 - Implement first-class asset register.
5. #135 - Implement module entitlements and one-module trials.
6. #136 - Add calendar and cross-module deadline notification hub.
7. #137 - Implement vulnerability scanning integration.
8. #138 - Define document editing and PDF-only finalized downloads.
9. #130 / #139 - Stabilize exports and complete data export coverage.
10. #141 - Add knowledge base and in-app guidance.
11. #142 - Model ISO governance registers and management review artefacts.
12. #143 - Define Axim operator product analytics and tenant usage metrics.
13. #129 - Evaluate replacing WeasyPrint PDF generation.
14. #140 - Maintain BRD/TRD/traceability and ADR updates as delivery progresses.
