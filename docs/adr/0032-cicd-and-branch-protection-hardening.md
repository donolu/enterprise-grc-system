# ADR-0032: CI/CD and branch-protection hardening

## Status
Proposed

## Context
CI already runs backend tests, frontend lint/type-check/build, security scanning (Trivy, Bandit, TruffleHog, hadolint), and a Docker build; CD deploys to Azure App Service with slot swaps and SBOMs (ADR-0007). The gap is enforcement: `main` has **no branch protection** (verified via the API: "Branch not protected"), so despite `.github/branch-protection-setup.md`, nothing requires a PR, requires the checks to pass, or blocks a direct push. Green CI that is not *required* is advisory.

Provena's setup made the individual jobs the required checks, required branches to be up to date, and enforced a branch-name convention tied to a real issue, which is what turned CI from advisory into a gate.

## Decision
Make the existing checks enforceable and keep the CI shape modern (the mechanics land in #71).

- **Branch protection on `main`:** require a PR; require status checks to pass and the branch to be **up to date** (strict); required contexts = Backend Tests, Frontend Tests, Security Scanning, and Branch name check; require linear history; block force-push and deletion.
- **Branch-name convention:** keep the pre-push hook and the `branch-name` workflow (`<type>/<issue#>-<desc>` tied to a real GitHub issue) as the required check.
- **CI shape:** modern `setup-python`/`setup-node`, correct dependency caching, split backend/frontend jobs, and path filtering, tracked in #71.

## Consequences
- No unreviewed or failing code reaches `main`; "green but not required" can no longer merge.
- Slightly more process for every change (a PR and an up-to-date branch); this is the intended trade for a compliance product.
- Requires the required-check names to match the workflow job names exactly.

## Alternatives considered
- Trust convention without protection (status quo): one accidental push to `main` undoes it.
- Require human review approvals now: valuable later, but with a small team the automated gates are the higher-leverage first step.

## References
- Issues #80, #71; ADR-0007 (CI/CD pipeline).
