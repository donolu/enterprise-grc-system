# Template Library Import Guide

## Purpose

The Axim ZIP contains reusable policy, standard, procedure, ISO mandatory, PCI, risk and asset documents. Admins may also upload individual template files later. These should be imported as template-library records that preserve the original Office files and add searchable GRC metadata.

The template library is separate from ordinary evidence uploads:

- `core.Document` stores the actual file and access logs.
- `catalogs.TemplateDocument` stores template metadata, source path, checksum, module classification and optional links to frameworks, clauses or controls.

## Admin Web Upload

Admins can upload a full ZIP pack or a single Office/PDF/spreadsheet document from the system administration page.

The web flow supports:

- file selection for `.zip`, Office, PDF, CSV and text files
- optional framework and framework-version linkage
- optional module and document-type overrides for single files
- preview before import
- persisted import audit events

## Import Command

```bash
python manage.py import_template_library "/path/to/Axim App.zip" \
  --user system \
  --framework PCI-DSS \
  --framework-version 4.0
```

Single files are also supported:

```bash
python manage.py import_template_library "/path/to/Access Control Policy.docx" \
  --user system \
  --module policy \
  --document-type policy
```

Use `--dry-run` first:

```bash
python manage.py import_template_library "/path/to/Axim App.zip" --dry-run
```

The importer is idempotent by `source_path`. For ZIP imports, the source path is the path inside the archive. For single-file web uploads, it is the uploaded filename. Re-running the import updates metadata and file content when needed, but it does not create duplicate template records.

## Classification

The importer classifies documents from their ZIP path:

- `Documentation Module/Policies` -> policy templates
- `Documentation Module/Standards` -> standard templates
- `Documentation Module/Procedure` -> procedure templates
- `ISO 27001 Mandatory Documents Module` -> ISO mandatory documents
- `PCI Module` -> PCI framework spreadsheet
- `Risk Register Module` -> risk register template
- `Asset Register Module` -> asset register template

It skips Mac/system files, hidden files, Office lock files and unsupported file types.

## Linkage

Framework linkage is explicit. Use `--framework` and `--framework-version` when importing framework-specific content such as the PCI workbook or ISO mandatory documents.

Clause and control linkage should not be guessed from broad document titles. Template records have nullable `framework`, `clause` and `control` links so curated mappings can be added later without changing the storage model.

Linked templates are discoverable through:

- `GET /catalogs/api/template-documents/`
- `GET /catalogs/api/clauses/{id}/templates/`
- `GET /catalogs/api/controls/{id}/templates/`
- control detail responses, via `template_documents`

## Audit Trail

Successful imports write a tenant-scoped `AuditEvent` named `TEMPLATE_LIBRARY_IMPORTED`.

The audit payload includes:

- source ZIP path
- importable, imported, updated and skipped counts
- module counts
- document-type counts
- importing user

## Current Axim ZIP Smoke Result

The supplied ZIP produced:

- 83 importable documents
- 6 skipped files
- 26 policy templates
- 23 procedure templates
- 21 standard templates
- 10 ISO mandatory documents
- 1 PCI workbook
- 1 risk register
- 1 asset register

The PCI workbook links to `PCI-DSS` when that framework exists and the import is run with `--framework PCI-DSS --framework-version 4.0`.
