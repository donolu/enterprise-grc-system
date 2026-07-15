# ADR 0038: Operator Product Analytics

## Status

Accepted

## Context

Axim needs product analytics for marketing, support and product improvement. Existing analytics endpoints are tenant-visible GRC dashboards, so they must not be reused as cross-tenant operator reporting without explicit privacy controls.

## Decision

Add an operator-only analytics endpoint at `/api/analytics/operator/usage/`.

The endpoint aggregates:

- tenant and subscription counts;
- plan and subscription status mix;
- module adoption based on enabled subscription modules;
- document upload, export, audit event, policy acknowledgement and training engagement counts;
- last activity timestamp per tenant.

The endpoint is restricted to staff/superusers authenticated on the public/platform schema and supports JSON plus CSV export through `?export=csv`. Tenant staff accounts are intentionally rejected because the response spans multiple tenants.

The reporting window uses timezone-aware server-side datetimes. A `days` filter represents a rolling absolute time window and is not derived from operator browser locale or geolocation.

## Privacy Controls

The operator response intentionally excludes tenant-owned content. It returns tenant identifiers, subscription state, enabled module keys, aggregate counts and last activity timestamps. It does not return document names, policy text, audit details, export titles, training titles, evidence content or user personal activity logs.

## Consequences

The first version uses durable business records that already exist rather than adding request-level analytics writes. This avoids extra write load on every API request and gives operators useful adoption and engagement signals immediately. If Axim later needs clickstream-style product analytics, that should be implemented as a separate event pipeline with sampling, retention and consent controls.
