# GRC SaaS Platform - Requirements Specification

## 1. Introduction
This document specifies the functional and non-functional requirements for the multi-tenant Governance, Risk, and Compliance (GRC) SaaS platform. It consolidates all initial requests and serves as the primary reference for the project's scope.

## 2. User Roles
*   **Company Admin:** Manages the tenant account, users, subscriptions, and billing. Has full access to all modules for their company.
*   **Compliance Manager:** Manages one or more compliance frameworks, assigns tasks, and tracks evidence.
*   **Risk Manager:** Manages the risk register and mitigation plans.
*   **Vendor Manager:** Manages vendor profiles and associated tasks.
*   **Standard User:** A general employee who interacts with the system to read/acknowledge policies, complete training, or act as an owner for specific tasks (risks, controls).

## 3. Functional Requirements

### 3.1. Core Platform & Tenant Management
*   **FR1.1 - Multi-Tenancy:** The platform must support multiple client companies (tenants) with complete data isolation.
*   **FR1.2 - Client Registration:** Clients shall be able to register their company on the platform.
*   **FR1.3 - Subscription Tiers:** The platform will offer three tiers:
    *   Free Version
    *   Paid Basic Version
    *   Paid Enterprise Version
*   **FR1.4 - User Management:** Company Admins must be able to add, manage, and remove users within their tenant, based on the number of seats allowed by their subscription.
*   **FR1.5 - Billing & Payments:** The system must handle recurring monthly/annual billing. It must integrate with a payment provider (Stripe) and support grandfathering of legacy pricing plans.
*   **FR1.6 - Trial Period:** A one-month trial for a single GRC module shall be available to new clients.

### 3.2. Security & Authentication
*   **FR2.1 - Two-Factor Authentication (2FA):** All users must be able to secure their accounts with 2FA, with email OTP as the baseline method.
*   **FR2.2 - Activity Tracking:** The system must maintain a detailed audit log of user activities (logins, uploads, downloads, changes) that is viewable by the client's admin.

### 3.3. Compliance Workflow Modules
*   **FR3.1 - Framework Support:** The system must support workflows for multiple GRC frameworks, including:
    *   ISO 27001, 20000, 22301
    *   PCI DSS
    *   NIST CSF, CIS Controls
    *   PSD2, GDPR
    *   (Future) SOC2, HIPAA, Cyber Essentials
*   **FR3.2 - Interactive Workflows:** For each framework, clients must be able to assess each control/clause, marking it as applicable (Yes/No).
*   **FR3.3 - Evidence Management:** Clients must be able to upload evidence (Word, PDF, images) to support their assessment for each control. The system must also provide downloadable templates/samples for required documentation.
*   **FR3.4 - External Document Upload:** Clients must be able to upload their own existing documents to satisfy a control, replacing the provided templates.
*   **FR3.5 - Document Storage:** All uploaded documents must be stored in a secure, central repository (Azure Blob Storage).

### 3.4. Risk Management Module
*   **FR4.1 - Risk Register:** A module for clients to populate and manage their risk register, based on a provided spreadsheet template.
*   **FR4.2 - Automated Risk Scoring:** The module must automatically calculate a risk rating based on user-specified Impact and Probability levels.
*   **FR4.3 - Risk Remediation & Evidence:** Users must be able to track remediation tasks and upload evidence (screenshots, documents) to show a risk has been addressed.

### 3.5. Vendor Management Module
*   **FR5.1 - Vendor Tracking:** A module for clients to manage their vendors, based on a provided spreadsheet template.
*   **FR5.2 - Interactive Date Tracking:** The module must track key dates and to-do activities for each vendor.

### 3.6. Policy & Document Management
*   **FR6.1 - Policy Repository:** A central repository to hold all of a client's completed policies, standards, and procedures.
*   **FR6.2 - Acknowledgement Workflow:** Policies can be sent to all staff, who must read and acknowledge them. The system will record acknowledgments and send reminders to those who have not complied.
*   **FR6.3 - Inline Editing:** Users shall be able to modify uploaded Word and spreadsheet documents directly within the browser.
*   **FR6.4 - Secure Download:** After modification, documents should be downloadable only in PDF format to protect integrity.

### 3.7. General Modules & Utilities
*   **FR7.1 - Automated Notifications:** The system must send email notifications and reminders for various events, including:
    *   Task deadlines (a week before and on expiry).
    *   Overdue risk remediation.
    *   Vendor activity dates.
    *   Policy acknowledgment reminders.
*   **FR7.2 - Information Security Awareness:** A module to schedule and send security awareness materials to all staff via email at regular intervals.
*   **FR7.3 - Video Training:** A module to provide video training content from Synthesia.io to all registered users.
*   **FR7.4 - Knowledge Base:** An embedded section with articles and guides on how to use the application.
*   **FR7.5 - Calendar Module:** A calendar for clients to populate with important dates and events, with associated email notifications.
*   **FR7.6 - Vulnerability Scanning:** A module that can connect to client systems to run vulnerability scans using an open-source tool and report on the findings.
*   **FR7.7 - Data Export:** Clients must be able to download all their data from any module in either spreadsheet or PDF format.
*   **FR7.8 - Analytics:** The platform admin must have access to analytics on tool performance and usage for marketing and improvement purposes.

## 4. Non-Functional Requirements
*   **NFR1 - Security:** The platform must enforce strict data isolation between tenants. All data should be encrypted in transit and at rest.
*   **NFR2 - Scalability:** The platform must be able to accommodate many different clients logging on and using the application simultaneously without performance degradation.
*   **NFR3 - Usability:** The user interface must be beautiful, modern, professional, and intuitive.

## 5. Technical & Deployment Constraints
*   **TC1 - Deployment Platform:** The application will be deployed on Microsoft Azure.
*   **TC2 - Source Control:** The source code will be managed in a GitHub repository.
*   **TC3 - Website CMS:** The public-facing marketing website will be a separate CMS (e.g., WordPress).
