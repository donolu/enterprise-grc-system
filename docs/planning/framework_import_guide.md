# Framework Import Guide

## Purpose

Frameworks such as ISO 27001, PCI DSS, NIST CSF and CIS Controls should be loaded as versioned catalogue data rather than hard-coded workflow logic. This keeps framework updates repeatable, auditable and tenant-safe.

## Supported Formats

Use the `import_framework` management command for structured framework imports:

```bash
python manage.py import_framework path/to/framework.json
python manage.py import_framework path/to/framework.yaml
python manage.py import_framework path/to/framework.xlsx \
  --name "PCI DSS" \
  --short-name PCI-DSS \
  --framework-version "4.0" \
  --issuing-organization "PCI Security Standards Council" \
  --effective-date 2022-03-31 \
  --sheet "Original Content"
```

Use `--dry-run` before a real import to verify the detected clause and control counts. Use `--update` only when replacing an existing framework with the same name and version.

## Spreadsheet Requirements

Spreadsheet imports require explicit metadata because workbooks usually do not carry reliable framework identity fields:

- `--name`
- `--framework-version`
- `--issuing-organization`
- `--effective-date`
- `--short-name` is optional but recommended because generated control identifiers use it.

The importer detects a header row containing a recognised ID column and a requirement/title column. Common aliases are supported, including:

- `PCI DSS ID`, `Requirement ID`, `Clause ID`, `ID`
- `Defined Approach Requirements`, `Requirement`, `Description`, `Control Objective`
- `Defined Approach Testing Procedures`, `Testing Procedures`, `Test Procedures`
- `Guidance`, `Implementation Guidance`
- `Evidence`, `Evidence Requirements`

Each importable row creates a clause. Rows with testing procedures, evidence requirements or an explicit control ID also create or update a linked control.

## Versioning

Framework versioning is based on the catalogue identity `(name, version)`.

- Importing a new version should use a new `--framework-version` value and creates a separate `Framework` record.
- Re-importing the same version requires `--update`; this replaces the framework's clauses and upserts generated controls.
- Imported frameworks store `imported_from` and `import_checksum` so the source file can be traced later.
- Do not use `--update` for an official version change. Create a new framework version instead so historical assessments can still reference the version they were performed against.

## Audit Trail

Successful imports write a tenant-scoped `AuditEvent` named `FRAMEWORK_IMPORTED`.

The audit payload includes:

- framework ID, name and version
- source file path
- source file checksum
- whether an existing framework version was updated
- imported clause and control counts
- importing user when `--user` is supplied

This gives operators enough evidence to answer when a catalogue version entered the tenant, what file was used and whether it was a replacement import.

## Future Frameworks

For each new framework:

1. Preserve the source spreadsheet or structured file in the controlled template library.
2. Run a dry-run import and record the detected counts in the PR.
3. Import into local/test data using a stable short name.
4. Add or update tests when a new spreadsheet shape introduces new headers.
5. Link relevant templates and sample documents to the imported clauses or controls in the template-library import work.
