# ADR-0027: Type-safe API client generated from the OpenAPI schema

## Status
Proposed

## Context
The backend already publishes an OpenAPI 3.0 schema via drf-spectacular (`/api/schema/`, Swagger at `/api/docs/`, ADR-0014). The Next.js frontend, however, calls the API through hand-written Axios functions with manually declared TypeScript types. Nothing keeps those types in step with the API, so a serializer change can silently break the client, and reviewers cannot see contract drift in a diff.

On Provena this class of bug was eliminated by generating the client types from the schema and failing CI when the committed types drift.

## Decision
Generate the frontend API types from the OpenAPI schema and treat them as a checked-in, CI-verified artefact.

- Add `openapi-typescript` and generate `frontend/src/lib/api/generated/schema.d.ts` from the exported schema.
- Commit the generated types; wrap them in thin typed service functions in `src/lib`.
- Add a CI job that re-exports the schema, regenerates the types, and **fails if the committed output differs** (the "verify OpenAPI types" gate). A bot must not auto-commit the regenerated file, because a token push would not re-trigger required checks.
- Migrate existing Axios calls onto the typed client incrementally, module by module.

## Consequences
- API contract changes surface as a types diff in review; breaking changes fail the build instead of production.
- One more CI job and a generation step in the frontend toolchain.
- Requires the schema to stay accurate (drf-spectacular warnings should trend to zero, as on Provena).

## Alternatives considered
- Hand-maintained types (status quo): cheap per-change, but drifts and offers no guarantee.
- Runtime validation (zod) only: guards responses at runtime but does not give compile-time safety or a review-time diff.

## References
- Issue #82; ADR-0014 (API documentation).
