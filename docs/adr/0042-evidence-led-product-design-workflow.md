# ADR-0042: Evidence-led product design workflow

## Status

Accepted

## Context

GRC Suite must support dense, high-consequence work without presenting generic dashboard templates, decorative empty states or actions that imply unavailable workflows. The local browser review of 11 August 2026 found visual inconsistency alongside functional dead ends. The platform already uses Ant Design, custom theme tokens and Playwright, but needs a repeatable decision process before further visual rework.

## Decision

Use an evidence-led workflow for material frontend changes.

1. **Audit the live flow first.** Capture fresh desktop and mobile screenshots of the relevant workflow, test primary actions and record console, navigation and accessibility defects as issues.
2. **Separate functional integrity from visual work.** Broken links, simulated actions and unavailable back-end capabilities must be fixed or made explicitly unavailable before visual polish.
3. **Explore before implementation.** Use Superdesign to analyse the existing frontend and create reviewable visual directions. Product Design is used for screenshot-led audit, visual exploration and implementation QA.
4. **Maintain an application-owned design reference.** Curated external `DESIGN.md` sources may inform the work, but GRC Suite keeps its own `frontend/DESIGN.md` containing approved tokens, layout rules, interaction states and component guidance. It must not copy another product's branding.
5. **Verify in the browser.** Frontend PRs that change a material workflow require desktop and mobile screenshot inspection, keyboard-path checks for primary controls, and no new console errors. Playwright remains the automated regression gate.

## Consequences

- Design proposals become reviewable before code commits, reducing rework and generic implementation drift.
- Functional truthfulness is a release requirement: visible actions work, or have an accessible unavailable state with a clear reason.
- The dashboard redesign in #392 follows this ADR after navigation integrity (#388) and real global search (#389).

## Alternatives considered

- Adopt a third-party design system wholesale: rejected because it would dilute the GRC product identity and retain external brand constraints.
- Continue ad-hoc page-by-page styling: rejected because it makes quality, accessibility and consistency difficult to review.

## References

- ADR-0031: Frontend design-system evolution.
- Issues #388, #389 and #392.
