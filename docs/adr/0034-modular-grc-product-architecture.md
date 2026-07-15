# ADR-0034: Modular GRC Product Architecture and Requirements Traceability

## Status

Accepted

## Context

The original business brief defines a broad multi-tenant GRC SaaS product covering frameworks, risk, vendor management, policies, documents, awareness training, calendar reminders, vulnerability scanning, billing, analytics and exports.

The codebase has already implemented substantial module foundations, but delivery now needs a more explicit programme-level architecture and traceability model. Without that, the project risks accumulating isolated modules that do not align with SaaS packaging, one-module trials, content import and audit-ready workflows.

## Decision

We will treat Axim GRC as a modular SaaS platform with shared platform services and independently packageable business modules.

### Platform Services

- Tenant isolation.
- Authentication and MFA.
- Subscription billing and module entitlements.
- Document storage.
- Audit logging.
- Notifications/reminders.
- Imports/exports.
- Analytics.
- OpenAPI/API contract.

### Business Modules

- Framework/control assessment.
- Risk management.
- Vendor management.
- Policy, standard and procedure repository.
- Training and awareness.
- Asset register.
- Calendar/deadline management.
- Vulnerability scanning.

## Key Decisions

### 1. Modules Must Be Entitlement-Aware

Each major module must be independently grantable or blockable by plan/trial. UI navigation alone is insufficient; API access must enforce the same entitlement model.

### 2. Content Must Be Imported and Versioned

Framework spreadsheets, control catalogs and document templates are product data. They should be imported idempotently with source checksums/version metadata instead of being hard-coded into business logic.

### 3. Document Templates and Evidence Must Link to Work Items

Templates, samples and evidence should be discoverable from the relevant framework/control/policy/risk/vendor/asset item. This is required for audit usability and client adoption.

### 4. Cross-Module Deadlines Need a Shared Calendar Layer

Individual modules may own due dates, but reminders and calendar views should be unified so users do not need to inspect every module separately.

### 5. Major External Engines Require ADRs Before Implementation

Document editing/conversion and vulnerability scanning introduce significant operational and security implications. They require separate ADRs before build-out.

## Consequences

### Positive

- Clearer product packaging for free/basic/enterprise and trials.
- Better alignment between original business requirements and engineering delivery.
- Repeatable framework/template onboarding.
- More coherent UX across modules.
- Stronger auditability and tenant isolation discipline.

### Negative / Tradeoffs

- More upfront modeling work before some features can be completed.
- Entitlements add checks across API and frontend surfaces.
- Content import requires governance around source files, versions and mappings.
- Cross-module calendar/export layers must tolerate partial module availability.

## Implementation Notes

- Requirements are tracked in [../planning/requirements_traceability_matrix.md](../planning/requirements_traceability_matrix.md).
- BRD lives in [../planning/business_requirements_document.md](../planning/business_requirements_document.md).
- TRD lives in [../planning/technical_requirements_document.md](../planning/technical_requirements_document.md).
- Gap tickets are ordered from foundation/content import through module completion and reporting.

## Related Issues

- #132 - Framework spreadsheet import.
- #133 - Template library import/linking.
- #134 - Asset register.
- #135 - Module entitlements and trial packaging.
- #136 - Calendar and deadline notification hub.
- #137 - Vulnerability scanning.
- #138 - Document editing and PDF-only finalized downloads.
- #139 - Data export coverage.
- #140 - BRD/TRD/traceability governance.
- #141 - Knowledge base and in-app guidance.
- #142 - ISO governance registers and management review artefacts.
- #143 - Axim operator product analytics and tenant usage metrics.
