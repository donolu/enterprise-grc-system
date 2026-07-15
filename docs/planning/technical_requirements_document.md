# Technical Requirements Document: Axim GRC SaaS

## Document Control

- **Product:** Multi-tenant Information Security GRC SaaS
- **Related BRD:** [business_requirements_document.md](business_requirements_document.md)
- **Traceability:** [requirements_traceability_matrix.md](requirements_traceability_matrix.md)
- **Architecture ADRs:** [../adr/0034-modular-grc-product-architecture.md](../adr/0034-modular-grc-product-architecture.md), [../adr/0039-audit-versioning-standard.md](../adr/0039-audit-versioning-standard.md)

## Current Architecture Baseline

The application is a Django/DRF backend using `django-tenants` schema isolation, PostgreSQL, Redis/Celery for asynchronous work, Azure-oriented tenant-aware blob storage, Stripe billing and a frontend backed by generated OpenAPI types. Existing modules include catalogs, exports, risk, vendors, policies, training, analytics, billing, SSO/authn and core document/audit models.

## Architecture Principles

1. **Tenant isolation first:** every client-owned record must be scoped by tenant schema or equivalent isolation boundary.
2. **Module-first product model:** frameworks, risk, vendors, policies, assets, training, calendar and scanning must be independently usable and packageable.
3. **Content as data:** frameworks, clauses, controls and document templates should be imported and versioned data, not hard-coded workflows.
4. **Evidence-grade auditability:** uploads, downloads, acknowledgments, exports and state changes must be auditable.
5. **Async for long-running work:** imports, PDF generation, exports, scanner jobs and bulk email tasks must run through workers.
6. **Security by default:** 2FA, least privilege, file validation, secure storage and dependency hygiene are product requirements, not afterthoughts.

## Major Components

### Backend

- Django and Django REST Framework.
- `django-tenants` for schema-based tenant isolation.
- PostgreSQL for relational data.
- Redis and Celery for background jobs.
- Azure Blob-compatible tenant-aware document storage.
- Stripe integration for billing and subscriptions.
- OpenAPI schema generation for frontend/client contracts.

### Frontend

- Web application consuming generated API client/types.
- Module-aware navigation driven by entitlements.
- Operational UI optimized for dashboards, workflows, tables, forms and evidence review.

### Asynchronous Processing

Required async domains:

- Framework/content imports.
- Template library imports.
- Email reminders.
- Policy acknowledgment reminders.
- PDF/report generation.
- Data exports.
- Vulnerability scan jobs.

## Data Domain Requirements

### Framework Catalog

Must support Framework, Clause, Control, ControlAssessment, evidence expectations, applicability, status, ownership, review dates and import metadata.

### Template Library

Must store template metadata and source documents. Documents must link to frameworks, clauses, controls, policies or other module items.

### Risk Register

Must calculate risk level from impact and likelihood/probability. Must support actions, owners, due dates, evidence and reminders.

### Vendor Management

Must support vendor profiles, categories, contacts, services, contracts, due diligence, tasks and reminders. Existing vendor APIs need route validation under #128.

### Policy Repository

Must support policy categories, versioned policy documents, distribution, acknowledgments, expiry and reminders.

### Asset Register

Must be added as a first-class module with owners, classification, criticality, review dates, linked risks/controls/evidence and import support.

### Calendar

Must aggregate cross-module deadlines and custom events, with owner notifications and idempotent reminder logs.

### Vulnerability Scanning

Must model targets, schedules, scan jobs and findings. Scanner workers must run with explicit network and credential boundaries.

### Exports

Must provide tenant-scoped CSV/XLSX/PDF exports for each module, with async lifecycle and audit logging.

## Audit, Versioning and History Requirements

The platform must follow [ADR 0039](../adr/0039-audit-versioning-standard.md) for evidence-grade audit trails and governed content history.

### Audit Event Standard

Material tenant activity must emit tenant-scoped audit events with a consistent payload where available:

- actor ID, email and actor type;
- object type, object ID and a short non-sensitive display label;
- event name;
- previous and new values for material changes;
- workflow reason or comment where applicable;
- source IP, user agent and request ID where request context exists;
- source type and reference for imports, workers and webhooks.

Audit details must not store document contents, evidence file contents, secrets, full payment provider payloads, access tokens or unnecessary personal activity logs.

### Immutable Versioning

Explicit immutable versions or history snapshots are required when a record's previous meaning may be needed as audit evidence. This applies to:

- framework catalogue data, including frameworks, clauses and controls;
- control assessments, applicability decisions and evidence state;
- policies, standards, procedures and final PDF artefacts;
- material risk decisions and risk scoring changes;
- vendor due diligence decisions, contract milestones and review outcomes;
- asset register ownership, classification and criticality changes;
- management review artefacts, non-conformities, scope documents and regulatory obligations.

Routine preferences, generated reminder attempts and read-only access events may use audit events without full historical snapshots unless they affect evidence, billing or access control.

### Retention and Visibility

Tenant-owned audit events must remain tenant-isolated and visible to authorised tenant administrators through audit views and exports. Platform/operator audit events must stay in the platform context and must not expose tenant-owned content.

Enterprise defaults should retain audit evidence for at least seven years unless a client contract requires a longer period. Deletion, anonymisation and retention policy changes must themselves be auditable.

### Implementation Sequence

- #159: shared audit event standard and retention controls.
- #160: framework catalogue versioning and audit coverage.
- #162: risk, vendor and asset audit/history coverage.
- #161: policy version audit standardisation.
- #163: document, export and download lifecycle audit coverage.
- #164: subscription, billing and entitlement audit coverage.

## Integration Requirements

- **Email:** 2FA, reminders, policy acknowledgment, training campaigns, billing and system notifications.
- **Stripe:** subscriptions, webhooks, billing portal, grandfathering and plan limits.
- **Azure Blob Storage:** tenant-scoped document storage.
- **Scanner Engine:** selected later via ADR before implementation.
- **Document Editing/Conversion:** selected later via ADR before inline editing/PDF-only delivery.
- **OpenAPI:** API schema remains the contract for frontend types and external clients.

## Security Requirements

- Email 2FA must remain available; TOTP may be offered as stronger option.
- All module APIs must enforce authentication, authorization and tenant isolation.
- File uploads must validate type and size.
- Final document downloads must respect permissions and lifecycle state.
- Scanner credentials must not be stored in plaintext.
- Import jobs must reject unsafe paths/system files.
- Reports and exports must not cross tenant boundaries.
- Audit events must cover critical user and admin activity.

## Module Entitlement Requirements

The product must support explicit module entitlements per tenant/subscription:

- Free plan: limited default functionality.
- Basic plan: configured subset and limits.
- Enterprise plan: all modules and higher limits.
- Trial: one selected module for one month.
- Grandfathered/custom subscriptions: custom limits and module grants.

API and UI access must both enforce entitlements.

## Content Import Requirements

- Imports must be idempotent.
- Imports must preserve source identifiers and checksums.
- Framework imports must support versioning.
- Template imports must classify content and link templates to controls/items.
- Import errors must be reportable and actionable.

## Quality Requirements

- Targeted tests for every new module.
- Tenant isolation tests for all tenant-owned modules.
- Coverage floors should continue increasing by app.
- E2E tests should cover the critical buyer workflows.
- ADRs should be added before introducing major external dependencies.

## Deployment Requirements

- Azure-compatible deployment remains supported.
- Architecture should remain platform-agnostic where practical.
- CI must run backend tests, frontend tests, linting, security scanning and branch checks.
- Long-running operational jobs should be observable and retry-safe.

## Open Technical Decisions

- Document editing approach: Office integration vs OnlyOffice/Collabora vs form-driven document generation.
- PDF generation replacement: ReportLab vs Playwright/Chromium vs other renderer.
- Vulnerability scanner: OpenVAS/Greenbone vs Nuclei or layered approach.
- Content import schema and ownership workflow.
- Product entitlement model granularity.
