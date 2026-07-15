# Customer Data Export Coverage

Customer data exports are tenant-scoped and generated asynchronously through `POST /api/exports/tenant-data-exports/`.
The export job writes either an Excel workbook (`xlsx`) or a zipped CSV archive (`csv_zip`), then exposes the generated
document through the standard document download lifecycle so downloads are access logged.

## Coverage

| Module | Included data | Formats |
| --- | --- | --- |
| Identity and audit | Users, document metadata, document access logs, audit events | `xlsx`, `csv_zip` |
| Frameworks and assessments | Frameworks, clauses, controls, control evidence, assessments, assessment evidence, templates, assessment reminders | `xlsx`, `csv_zip` |
| Risk | Risk categories, matrices, risks, notes, actions, action notes, action evidence, action reminders | `xlsx`, `csv_zip` |
| Vendors | Regional configuration, categories, vendors, contacts, services, notes, tasks | `xlsx`, `csv_zip` |
| Policies | Categories, policies, versions, version audit logs, acknowledgements, distributions | `xlsx`, `csv_zip` |
| Training | Categories, videos, awareness campaigns, deliveries, video views | `xlsx`, `csv_zip` |
| Knowledge | Categories, articles, article revisions | `xlsx`, `csv_zip` |
| Compliance governance | Governance artefacts, regulatory requirements, non-conformities, management reviews | `xlsx`, `csv_zip` |
| Assets | Assets and asset review reminders | `xlsx`, `csv_zip` |
| Calendar | Events, notification preferences, reminder logs, calendar audit logs | `xlsx`, `csv_zip` |
| Vulnerabilities | Scan targets, schedules, jobs, vulnerability findings | `xlsx`, `csv_zip` |

## Controls

- Exports run inside the active tenant schema, so records from other clients are not queried.
- Only authenticated users can request, inspect or download their own export jobs.
- The export service excludes password, token, secret and Stripe identifier fields.
- File fields export metadata paths only, not the binary source files themselves.
- The coverage manifest is exposed at `GET /api/exports/tenant-data-exports/coverage/` for frontend discovery.
