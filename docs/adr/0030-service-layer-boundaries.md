# ADR-0030: Service-layer boundaries between apps

## Status
Proposed

## Context
The backend is a Django project split into domain apps (`risk`, `catalogs`, `policies`, `training`, `vendors`, `exports`, `core`, `authn`), but only three `services.py` modules exist. Cross-domain logic reaches directly into other apps' models and querysets from views and tasks. That coupling makes each domain hard to reason about, test, or extract, and it spreads tenant-scoping and permission logic across view code.

Provena runs the same modular-monolith shape with one rule that kept the domains clean: **inter-app calls go through `services.py`, never through direct model imports**, and views/tasks stay thin.

## Decision
Adopt an explicit service-layer boundary.

- Each app owns a `services.py` that encapsulates its business logic and is the only supported entry point for other apps.
- Views and Celery tasks delegate to services; they do not embed cross-domain queries.
- Cross-domain reads/writes call the owning app's service, not its models.
- New code follows the rule; existing hotspots are refactored opportunistically, starting where domains are most entangled (risk ↔ catalogs ↔ vendors).

## Consequences
- Clear seams for testing (services are unit-testable without HTTP) and for future extraction if a domain ever needs its own service.
- Tenant-scoping and permission checks concentrate in one place per domain.
- Some upfront churn moving logic out of views; done incrementally, not as a big-bang rewrite.

## Alternatives considered
- Keep direct model access: least effort, but the coupling and duplicated tenant logic get worse as the platform grows.
- Split into microservices now: premature for the current stage and scale; loses the simplicity of the monolith.

## References
- Issue #87.
