# ADR 0035: Document Editing And Final PDF Workflow

## Status

Accepted

## Context

The product needs a way for tenants to customise provided policy, standard, procedure and spreadsheet templates, preserve editable source material, and restrict final downloads to PDF for normal users.

Browser-native editing of Word and spreadsheet files is not realistic without a dedicated editor service. The practical choices are:

- integrate OnlyOffice or Collabora for inline Office editing;
- use Microsoft 365 or Google Workspace APIs;
- keep editing outside the app for now, then upload the edited source and finalise through a controlled PDF workflow;
- replace documents with app-managed forms and generated output.

## Decision

Use a phased workflow:

1. Templates and source documents remain stored as editable source files with restricted access.
2. Authorised editors customise documents outside the app and upload the modified source as a policy version.
3. Approved policy versions are finalised into a PDF artefact.
4. Normal users download only the final PDF.
5. Source downloads remain available only to authorised editors and administrators.
6. Every upload, edit, approval, finalisation, source download, PDF download and conversion failure is audited.

Office-to-PDF conversion is an optional worker/runtime capability. PDF sources can be finalised directly. DOC and DOCX conversion requires the LibreOffice binary to be available and `POLICY_ENABLE_OFFICE_CONVERSION=1`.

## Consequences

- The product now enforces final PDF downloads without pretending inline Office editing is available.
- Editable source files remain protected for administrators, policy owners, approvers and version creators.
- Inline editing can be added later by replacing the source-edit step with OnlyOffice or Collabora callbacks while preserving the same lifecycle and audit model.
- Conversion failures are explicit and auditable.
