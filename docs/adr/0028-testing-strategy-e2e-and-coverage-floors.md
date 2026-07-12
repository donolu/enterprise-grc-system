# ADR-0028: Testing strategy: frontend E2E, per-app coverage floors, tenant-isolation suite

## Status
Proposed

## Context
Test confidence is uneven. The frontend has no tests at all (`npm test` is a stub). On the backend, CI enforces a single global `--cov-fail-under=70`, and only the `risk` app has structured tests, and a global floor lets a well-covered app hide untested ones (`catalogs`, `policies`, `training`, `vendors`, `exports`, `core`, `authn`). For a multi-tenant GRC product sold on its control assurance, this is the wrong risk profile: the most security-critical property (tenant isolation) has no dedicated tests.

Provena's model (a required Playwright E2E gate plus per-app coverage floors) kept regressions out of the critical paths.

## Decision
Adopt a three-part testing strategy.

1. **Frontend tests.** Add Vitest + Testing Library for component/unit tests, and a Playwright E2E suite covering the critical GRC journeys (login, tenant context, risk register CRUD, policy acknowledgement, vendor profile, assessment flow). E2E runs against the compose stack and is a **required** CI check.
2. **Per-app backend coverage floors.** Replace the single global threshold with a per-app floor computed from `coverage.json` (start at each app's current level, ratchet toward a common target). New code lands with tests for its app.
3. **Tenant-isolation suite.** A dedicated suite asserting that a principal in tenant A can never read or write tenant B data across every API viewset, export, and Azure Blob path, plus the public/tenant schema split. This is a required check (see ADR-0029).

## Consequences
- Higher upfront cost writing the first frontend and cross-tenant tests; durable protection of the paths that matter for compliance buyers.
- Slightly longer CI; mitigated by path-filtering and parallel jobs.
- Coverage floors must be seeded per app to avoid blocking on day one.

## Alternatives considered
- Keep the global 70% floor: simplest, but structurally unable to protect under-tested apps.
- Manual QA of tenant isolation: not repeatable and not auditable, which is unacceptable for the core security boundary.

## References
- Issues #81, #83, #84; ADR-0029 (security hardening).
