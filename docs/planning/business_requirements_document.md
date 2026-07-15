# Business Requirements Document: Axim GRC SaaS

## Document Control

- **Product:** Multi-tenant Information Security Governance, Risk and Compliance SaaS
- **Audience:** Founder/product owner, engineering, delivery, compliance SMEs and implementation partners
- **Status:** Baseline BRD
- **Related TRD:** [technical_requirements_document.md](technical_requirements_document.md)
- **Traceability:** [requirements_traceability_matrix.md](requirements_traceability_matrix.md)

## Executive Summary

Axim GRC is a multi-tenant SaaS platform for managing information security certifications, risk assessments, vendor management, policies, standards, procedures, awareness training, evidence and audit-ready reporting. The platform should let each client operate one module independently or combine modules into a joined GRC operating model.

The current codebase already contains substantial foundations for tenant isolation, framework/control assessments, evidence storage, risk management, policy acknowledgments, training campaigns, analytics, billing and 2FA. The remaining business work is to load the supplied GRC content, close module gaps, formalize product packaging and harden document workflows.

## Business Goals

1. Provide a practical GRC workflow tool for SMEs and enterprise clients.
2. Support certification readiness for ISO 27001, ISO 20000, ISO 22301, PCI DSS, NIST CSF and future frameworks.
3. Reduce client effort by linking templates, samples and evidence expectations to relevant controls/items.
4. Provide recurring SaaS revenue through free, basic and enterprise tiers.
5. Support controlled trials that demonstrate value without exposing the full product.
6. Preserve tenant data isolation and auditability as core trust requirements.
7. Produce exportable evidence, reports and management information for audits and executive reviews.

## Target Users

- **Client administrator:** Configures company account, users, modules, subscriptions and document repositories.
- **Compliance manager:** Owns frameworks, control applicability, evidence collection and certification readiness.
- **Risk manager:** Maintains risk register, actions, owners, due dates and remediation evidence.
- **Vendor manager:** Tracks supplier due diligence, contracts, reviews and vendor tasks.
- **Policy owner:** Publishes policies, standards and procedures and tracks acknowledgments.
- **Staff user:** Completes assigned acknowledgments, training and evidence/action tasks.
- **Axim operator:** Supports tenants, monitors adoption, manages billing and reviews analytics.

## Product Scope

### Core Modules

- Framework and certification workflows.
- Risk management.
- Third-party/vendor management.
- Asset management.
- Policy, standard and procedure repository.
- Evidence and document storage.
- Security awareness and training.
- Calendar/deadline notifications.
- Vulnerability scanning.
- Analytics and reporting.
- Billing and subscription management.

### Frameworks and Content Packs

Initial content should support:

- ISO 27001.
- ISO 20000.
- ISO 22301.
- PCI DSS guide.
- NIST CSF.
- CIS Controls.
- PSD2.
- GDPR.
- SOC 2, HIPAA, Cyber Essentials and additional frameworks later.

Framework content will be imported from provided spreadsheets/documents and represented as reusable catalogs of frameworks, clauses, controls, evidence expectations and documentation links.

### Supplied Template Library

The source archive `Axim App-20260715T065616Z-1-001.zip` contains policy, standard, procedure, ISO mandatory, PCI, risk register and asset register files. These must become a governed in-app template/sample library, not just static files.

Users must be able to:

- Find templates from relevant controls/items.
- Download editable templates when permitted.
- Upload existing or customized external documents.
- Keep completed documents in the tenant repository.
- Download finalized documents as PDF where required.

## Business Requirements

### BR-001 Multi-Tenancy

The application must support multiple client organizations using the platform simultaneously with strict data separation.

### BR-002 Authentication and 2FA

The application must support secure login with at least email-based 2FA. TOTP support is desirable and currently available.

### BR-003 Subscription Plans

The application must support free, basic and enterprise versions, recurring billing, grandfathering and feature limits.

### BR-004 One-Module Trial

The application must support a one-month trial restricted to one selected module/item.

### BR-005 Framework Workflows

Clients must be able to select applicable controls, answer yes/no applicability questions, assign owners, provide evidence and track completion.

### BR-006 Template and Sample Linkage

Sample/template documents must be linked to relevant controls/items and downloadable/customizable by clients.

### BR-007 Document Repository

The application must store client documents, uploaded evidence, finalized policies and generated reports in a secure repository.

### BR-008 Risk Management

The application must support a risk register where rating is calculated from impact and probability/likelihood, with owners, due dates, actions and remediation evidence.

### BR-009 Vendor Management

The application must support vendor records, due diligence, contract/review dates, tasks and notification workflows.

### BR-010 Policy Acknowledgment

Policies, standards and procedures must be distributable to staff for reading and acknowledgment, with reminders and audit records.

### BR-011 Awareness and Training

The application must support awareness materials and video training, including scheduled email campaigns.

### BR-012 Calendar and Deadline Reminders

Deadline dates should notify task owners one week before expiry and on expiry. The platform should expose important dates in a shared calendar.

### BR-013 Vulnerability Scanning

The application should support vulnerability scanning against approved client systems using an open-source scanner and report findings.

### BR-014 Audit Activity Tracking

The application must track user logins, downloads, uploads, changes and other significant activity.

### BR-015 Analytics

Axim must be able to see product usage and performance analytics for marketing, support and product improvement.

### BR-016 Data Export

Clients must be able to download their module data in spreadsheet and/or PDF formats.

### BR-017 Future Framework Expansion

The product must support adding further frameworks without major code changes.

## Non-Functional Requirements

- Strong tenant isolation.
- Auditable workflows.
- Secure file handling.
- Email notification reliability.
- Azure-compatible deployment with future platform portability.
- GitHub-based development and CI/CD.
- Scalable architecture that supports modular product packaging.
- Accessible, professional UI suitable for repeated operational use.

## Success Measures

- A new tenant can register, choose a plan/trial and access only entitled modules.
- A tenant can complete a framework assessment with linked templates and evidence.
- A tenant can maintain a risk register and receive due-date reminders.
- A tenant can manage policies and track acknowledgments.
- A tenant can export audit-ready evidence/reports.
- Axim can onboard additional framework content through import/configuration rather than custom code.

## Out of Scope for Current Baseline

- Custom CMS/marketing site implementation.
- Full inline Office editing until the document editing architecture decision is made.
- Live vulnerability scanning until scanner architecture and security boundaries are approved.
- Native mobile applications.

