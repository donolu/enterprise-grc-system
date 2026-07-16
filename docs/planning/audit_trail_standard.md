# Audit Trail Standard

This note operationalises [ADR 0039](../adr/0039-audit-versioning-standard.md).

## Event Shape

Tenant-scoped audit events should be written through `core.audit.log_audit_event()` so each event includes:

- actor identity and actor type;
- object type, object ID and optional non-sensitive display label;
- event name;
- previous and new values for material changes;
- workflow reason or comment where applicable;
- request IP, user agent and request ID where available;
- source type and source reference for imports, workers and webhooks.

Callers must not place document contents, evidence contents, secrets, full payment payloads, access tokens or unnecessary personal activity logs in `details`.

## Retention

Enterprise deployments should retain tenant audit evidence for at least seven years unless the client contract or applicable regulation requires longer retention.

Retention changes, deletion jobs and anonymisation jobs must themselves emit audit events. Where a legal hold applies, retention jobs must skip the affected tenant or record set.

## Tenant Visibility and Exports

Authorised tenant administrators should be able to review tenant-owned audit records through audit views and tenant data exports. Exported audit data should include event name, timestamp, actor summary, object type, object ID, source and request metadata.

Platform/operator events must remain in the platform context and must not include tenant-owned content. Cross-tenant product analytics should consume aggregate audit counts only.

