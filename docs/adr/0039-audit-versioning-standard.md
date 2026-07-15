# ADR 0039: Audit Trail and Versioning Standard

## Status

Accepted

## Context

Axim GRC must provide evidence-grade auditability across certifications, risks, vendors, assets, documents, policies, exports, billing and administrative actions. The codebase already has useful foundations, including `core.AuditEvent`, policy version audit logs, calendar audit logs, SSO audit logs, document access logs and framework import audit events.

The coverage is uneven. Some modules keep immutable versions, some keep timestamps only, and audit payloads do not yet share a common structure. That makes compliance evidence harder to review and makes future exports, admin views and security monitoring harder to standardise.

## Decision

Use a two-layer standard:

1. **Immutable history for governed content:** create explicit version or history records where the business meaning of a record must be preserved after change.
2. **Standard audit events for material activity:** emit tenant-scoped audit records for important create, update, delete, access, approval, import, export and workflow actions.

The existing `core.AuditEvent` remains the default tenant-scoped audit event store. Domain-specific history models remain valid where they preserve content lifecycle semantics, such as policy versions or future assessment snapshots. Domain-specific audit logs should either be aligned to the shared payload shape or mirrored into `AuditEvent` when tenant administrators need a single audit trail.

## Standard Audit Payload

Audit event details should use this shape where the data is available:

```json
{
  "actor": {
    "id": "user id or null",
    "email": "user email or service account",
    "type": "user|system|worker|webhook"
  },
  "object": {
    "type": "app.ModelName",
    "id": "primary key",
    "display": "short non-sensitive label"
  },
  "event": "DOMAIN_ACTION_NAME",
  "previous": {
    "field": "old value"
  },
  "new": {
    "field": "new value"
  },
  "reason": "workflow comment, review note or system reason",
  "request": {
    "ip": "source IP where available",
    "user_agent": "user agent where available",
    "request_id": "request correlation id where available"
  },
  "source": {
    "type": "api|admin|import|worker|webhook",
    "reference": "import id, webhook id or task id"
  }
}
```

Audit details must not store document contents, evidence file contents, secrets, full Stripe payloads, access tokens or unnecessary personal activity logs. Store identifiers and short non-sensitive labels instead.

## Versioning Rules

Use explicit immutable versions or snapshots for:

- frameworks, clauses and controls when official content changes;
- control assessments and evidence state where historical audit meaning must be preserved;
- policies, standards and procedures;
- approved documents and final PDFs;
- risk scoring methodology and material risk decisions;
- vendor due diligence decisions and contract lifecycle milestones;
- asset register records where classification, ownership or criticality changes affect compliance evidence;
- management review artefacts, non-conformities, scope documents and regulatory obligations.

Use standard audit events without full historical versions for:

- routine preference changes;
- generated reminders and notification attempts;
- read-only downloads or access events;
- transient worker lifecycle events, unless they affect evidence or billing;
- product analytics aggregation.

## Retention and Visibility

Tenant-owned audit events are tenant-scoped and should be visible to authorised tenant administrators through audit views and exports. Platform/operator audit events must stay in the platform context and must not expose tenant content.

Retention should be configurable by deployment, but enterprise defaults should retain audit evidence for at least seven years unless a client contract requires longer retention. Deletion or anonymisation must preserve compliance obligations and should itself be auditable.

## Implementation Tickets

- #159: shared audit event standard and retention controls.
- #160: framework catalogue versioning and audit coverage.
- #162: risk, vendor and asset audit/history coverage.
- #161: policy version audit standardisation.
- #163: document, export and download lifecycle audit coverage.
- #164: subscription, billing and entitlement audit coverage.

## Consequences

The platform gets a consistent audit contract without forcing every module into the same persistence model. High-risk governed content keeps immutable versions, while routine actions use audit events. This keeps storage growth manageable and gives tenant administrators, operators and auditors a clearer evidence trail.

