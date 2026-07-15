# ADR 0036: Tenant Knowledge Base and Contextual Guidance

## Status

Accepted

## Context

The BRD requires an embedded knowledge base and guidance on how to use the application. The product already has technical documentation, but tenants need searchable in-app guidance linked to modules and workflows. Admin users also need to update guidance without code changes.

## Decision

Add a tenant-scoped `knowledge` app with:

- Categories for organising guidance by module.
- Articles with draft, published and archived states.
- A `content_scope` field to distinguish tenant-authored guidance from Axim-managed global guidance.
- Module and workflow keys for contextual help.
- Article revisions as a lightweight audit trail for content changes.
- DRF endpoints for category/article management, published user access and contextual guidance lookup.

Tenant schema isolation remains the primary data boundary. Global guidance is represented as managed article content inside each tenant schema, which keeps reads simple and avoids cross-schema public content joins in user-facing requests.

## Consequences

- Staff users can publish and update guidance through API and Django admin without code changes.
- Normal users can only read published articles from active categories.
- Contextual help widgets can call `GET /api/knowledge/articles/contextual/?module_key=...&workflow_key=...`.
- Customer data exports include knowledge categories, articles and revisions so tenant records remain portable.
