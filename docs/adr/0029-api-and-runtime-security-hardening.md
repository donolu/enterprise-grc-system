# ADR-0029: API and runtime security hardening

## Status
Proposed

## Context
The production settings already set sensible transport and header defaults (HSTS, SSL redirect, secure cookies, nosniff, X-Frame-Options DENY). Three gaps remain for a multi-tenant GRC SaaS:

- **No rate limiting.** No `DEFAULT_THROTTLE_CLASSES` is configured, so authentication, export, and evidence-upload endpoints are unthrottled and open to brute force and abuse.
- **No error/latency visibility.** There is no Sentry or metrics wiring in the Django settings; production failures and Celery task health are effectively invisible.
- **Small config-hygiene issues.** `production.py` prints `ALLOWED_HOSTS` to stdout at import (leaks configuration into logs), and there is no explicit `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS` allowlist for the public origins.

## Decision
Harden the API and runtime along the lines proven on Provena.

- **Throttling.** Enable DRF throttling: anonymous and authenticated default rates, plus scoped throttles for login/2FA, exports, and evidence upload. Limits are env-tunable.
- **Observability.** Wire Sentry for backend and frontend (release + environment + tenant tags) and expose request/latency/error metrics (Prometheus endpoint or Azure Application Insights), including Celery task success/failure.
- **Config hygiene.** Remove the `print()` of `ALLOWED_HOSTS`; add explicit `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` allowlists; keep secrets out of the repo and evaluate GitGuardian alongside the existing TruffleHog/Trivy scanning.

## Consequences
- Brute-force and scraping surfaces are bounded; incidents become observable with tenant context.
- A little more configuration and two new runtime dependencies (Sentry SDKs).
- Throttle limits need tuning against real traffic to avoid false positives.

## Alternatives considered
- Rely on the Azure Front Door / WAF for rate limiting only: useful at the edge but does not protect per-user or per-scope semantics inside the app.
- Logs-only observability: no aggregation, alerting, or release correlation.

## References
- Issues #85, #86, #89; ADR-0028 (tenant-isolation tests).
