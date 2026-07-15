# ADR 0037: ISO Governance Registers and Management Review Artefacts

## Status

Accepted

## Context

The Axim requirements identify a regulatory and contractual sheet, non-conformity log, scope document, metrics, agenda and management review meeting artefacts. These need first-class treatment so tenants can search, evidence, export and audit them instead of storing them only as unstructured files.

## Decision

Use the existing tenant-scoped `compliance` app for ISO governance artefacts:

- `RegulatoryRequirement` stores regulatory, contractual, standard and policy obligations.
- `NonConformity` stores audit and assessment findings through corrective-action closure.
- `ManagementReview` stores meeting inputs, outputs, decisions, actions and links to findings.
- `GovernanceArtefact` classifies scope documents, metrics packs, agendas, management review packs, regulatory sheets and non-conformity logs.

All four record types link to controls, documents and other relevant modules. Customer data exports include the full governance set for audit readiness.

## Consequences

Structured records are now the authoritative workflow/search/reporting layer. Uploaded Word, spreadsheet or PDF documents remain evidence or templates linked to those records. This keeps scope documents and meeting packs governed without forcing every artefact into a bespoke workflow.
