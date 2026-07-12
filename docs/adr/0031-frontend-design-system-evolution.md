# ADR-0031: Frontend design-system evolution

## Status
Proposed

## Context
The frontend uses Next.js + Ant Design 5 with a custom light/dark theme (`frontend/src/theme.tsx`) built on a professional token palette (ADR-0025, ADR-0026). The foundation is good, but styling and layout are applied ad hoc per page: spacing, empty/loading/error states, and data visualisations vary, and there is no single documented source of truth. For a GRC product, the dashboards are the product: buyers judge control assurance by how clearly risk posture and compliance readiness are presented, and enterprise/government procurement increasingly requires demonstrable accessibility.

## Decision
Evolve the current theme into a documented, accessible design system rather than rebuild it.

- **Tokens as the single source of truth.** Consolidate palette, spacing, typography, radius, and elevation into tokens consumed by `ConfigProvider`, and stop per-page ad-hoc styles.
- **GRC visualisation kit.** Reusable components for the domain: risk **heat map**, compliance **posture gauge**, control-coverage and framework-readiness widgets, and trend sparklines, consistent across risk, assessments, vendors, and analytics.
- **Accessibility to WCAG 2.1 AA.** Contrast, visible focus, full keyboard operation, and ARIA on interactive widgets; verified with automated axe checks in the Playwright suite (ADR-0028).
- **Page templates and states.** Shared list/detail/dashboard templates with standard empty, loading, and error states so every module feels like one product.

## Consequences
- A more coherent, more sellable UI and a faster path to new screens.
- Accessibility becomes testable and defensible in security questionnaires.
- Some rework of existing pages onto the templates; sequenced behind the token consolidation.

## Alternatives considered
- Replace Ant Design with a bespoke Tailwind system (as on Provena): high cost and throws away working, accessible enterprise components for little benefit here.
- Leave styling per-page: cheapest, but the inconsistency is already a drag on velocity and perceived quality.

## References
- Issue #88; ADR-0025, ADR-0026 (existing UI theme).
