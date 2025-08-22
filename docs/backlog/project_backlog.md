## Project Backlog

### EPIC 0: Foundations & Core Setup

*Objective: Establish the core technical foundation of the application, including the project structure, multi-tenancy, user authentication, billing, and deployment pipelines.*

#### User Stories:

*   **Story 0.1: Scaffold New Project Structure**
    *   **Status:** Done
    *   **Description:** As a Developer, I need to create the new Django project layout as defined in the blueprint, with separate directories for settings (`app/settings/`), modular applications (`core`, `authn`, etc.), and infrastructure (`infra/`, `docker/`).
    *   **Acceptance Criteria (AC):**
        1.  The repository contains the new directory structure.
        2.  A `requirements.txt` file is created with all specified dependencies.
        3.  The project is configured with split settings for `local` and `production`.
        4.  A `Dockerfile` and `compose.yml` are created to run the local development environment.
    *   **What was achieved:**
        1.  ✅ Complete modular Django project structure with apps: `core`, `authn`, `catalogs`, `compliance`, `risk`, `vendors`, `policies`, `training`, `vuln`, `events`, `audit`, `exports`, `search`, `api`
        2.  ✅ Comprehensive `requirements.txt` with all production dependencies including Django, DRF, django-tenants, Celery, WeasyPrint, Azure integrations
        3.  ✅ Split settings architecture (`app/settings/base.py`, `local.py`, `production.py`)
        4.  ✅ Multi-service Docker environment with PostgreSQL, Redis, Azurite, MailHog, OnlyOffice, OpenSearch, and Flower
        5.  ✅ Additional infrastructure: Makefile for common operations, proper middleware stack, Celery configuration
        6.  ✅ Development environment fully functional with hot reloading and all services integrated

*   **Story 0.2: Implement Multi-Tenancy (Schema per Tenant)**
    *   **Status:** Done
    *   **Description:** As a System Architect, I need to configure `django-tenants` to ensure complete data isolation for each client company using separate PostgreSQL schemas.
    *   **AC:**
        1.  When a new `Tenant` is created, a corresponding PostgreSQL schema is automatically created.
        2.  User and all tenant-specific data are created within the tenant's schema.
        3.  Middleware correctly identifies the tenant based on the request's subdomain (e.g., `client-a.grc.com`).
        4.  Users from one tenant cannot access data from another.
    *   **What was achieved:**
        1.  ✅ Full django-tenants integration with PostgreSQL schema isolation
        2.  ✅ Automatic schema creation via `create_tenant` management command
        3.  ✅ Tenant resolution via subdomain middleware (django-tenants)
        4.  ✅ Complete data isolation verified - users cannot cross-access tenants
        5.  ✅ Shared vs tenant app separation properly configured
        6.  ✅ Database migrations working for both shared and tenant schemas

*   **Story 0.3: Implement User Authentication & Registration**
    *   **Status:** Done
    *   **Description:** As a User, I want to be able to register an account, log in with my email and password, and log out.
    *   **AC:**
        1.  A user registration page allows new users to sign up.
        2.  Users can log in using their email and password.
        3.  A robust password policy is enforced.
        4.  Users can log out, which invalidates their session.
        5.  The `core.User` model is linked to a `Tenant`.
    *   **What was achieved:**
        1.  ✅ RESTful API endpoints for registration (`POST /api/auth/register/`)
        2.  ✅ Login with username/email and password (`POST /api/auth/login/`)
        3.  ✅ Comprehensive password policy (8+ chars, complexity rules)
        4.  ✅ Session-based logout with CSRF protection (`POST /api/auth/logout/`)
        5.  ✅ User-tenant relationship via schema isolation (django-tenants approach)
        6.  ✅ Additional endpoints: profile management, password changes, user info
        7.  ✅ Complete multi-tenant isolation verified and tested

*   **Story 0.4: Implement Two-Factor Authentication (2FA)**
    *   **Status:** Done
    *   **Description:** As a User, I want to secure my account by enabling comprehensive Two-Factor Authentication with multiple methods including email, TOTP authenticator apps, and push notifications.
    *   **AC:**
        1.  Users can enable/disable 2FA in their account settings.
        2.  If 2FA is enabled, after entering their password, the user is prompted for a one-time code sent to their email.
        3.  Login is successful only after providing the correct OTP.
    *   **What was achieved:**
        1.  ✅ **Email 2FA** - Complete email-based OTP system with django-otp
        2.  ✅ **TOTP Authentication** - Authenticator app support (Google Authenticator, Authy, etc.)
        3.  ✅ **Push Notifications** - Custom PushDevice model for mobile app approvals
        4.  ✅ **Multi-method Support** - Users can enable multiple 2FA methods simultaneously
        5.  ✅ **User Preferences** - Configurable primary method and fallback priorities
        6.  ✅ **Intelligent Login Flow** - Automatic method selection based on user preferences
        7.  ✅ **Comprehensive API** - 10+ RESTful endpoints for complete 2FA management:
            - `/api/auth/2fa/status/` - Get current 2FA status and available methods
            - `/api/auth/2fa/enable/` - Enable email or push 2FA
            - `/api/auth/2fa/disable/` - Disable specific or all 2FA methods
            - `/api/auth/2fa/verify/` - Verify OTP codes from any method
            - `/api/auth/2fa/setup-totp/` - Generate QR codes for TOTP setup
            - `/api/auth/2fa/confirm-totp/` - Confirm TOTP setup with verification
            - `/api/auth/2fa/register-push/` - Register push notification devices
            - `/api/auth/2fa/approve-push/` - Handle push challenge approvals
            - `/api/auth/2fa/preferences/` - Manage user 2FA preferences
        8.  ✅ **Enterprise Features** - Device management, challenge expiration, audit trails
        9.  ✅ **Multi-tenant Integration** - Full compatibility with django-tenants isolation
        10. ✅ **Security Best Practices** - Secure token generation, challenge expiration, proper validation

*   **Story 0.5: Setup Subscription & Billing (Stripe)**
    *   **Status:** Done
    *   **Description:** As a Company Admin, I want to subscribe to a plan (Free, Basic, Enterprise) and manage my billing information.
    *   **AC:**
        1.  Integrate the Stripe API for subscription management.
        2.  Create webhook endpoints to listen for Stripe events (e.g., `checkout.session.completed`, `invoice.payment_succeeded`).
        3.  The application correctly assigns a plan to a tenant based on their subscription.
        4.  Implement logic for grandfathering prices.
        5.  A "Billing Portal" allows admins to view invoices and manage their subscription.
    *   **What was achieved:**
        1.  ✅ **Complete Stripe Integration** - Full Stripe API integration with test products and pricing
        2.  ✅ **Subscription Management Models** - Plan, Subscription, and BillingEvent models with tenant isolation
        3.  ✅ **RESTful Billing API** - 5+ endpoints for subscription management:
            - `GET /api/billing/current_subscription/` - View current tenant subscription
            - `POST /api/billing/create_checkout_session/` - Initiate subscription upgrade/downgrade
            - `POST /api/billing/cancel_subscription/` - Cancel subscription at period end
            - `GET /api/billing/billing_portal/` - Access Stripe customer portal
            - `GET /api/plans/` - List all available subscription plans
        4.  ✅ **Comprehensive Webhook Processing** - Complete webhook handler for all Stripe events:
            - `checkout.session.completed` - Process successful subscription purchases
            - `customer.subscription.*` - Handle subscription lifecycle events
            - `invoice.payment_succeeded/failed` - Track payment status
            - Automatic local subscription synchronization with Stripe
        5.  ✅ **Plan Feature Enforcement** - Robust plan limit system:
            - Document upload limits (50/500/10000 based on plan)
            - User limits (3/10/100 based on plan)
            - Feature access control (API access, advanced reporting, priority support)
            - Real-time usage tracking and limit validation
        6.  ✅ **Grandfathering Support** - Custom pricing and legacy plan support for existing customers
        7.  ✅ **Stripe Customer Portal** - Full integration with Stripe's hosted billing portal for invoice management
        8.  ✅ **Three-Tier Plan Structure** - Free ($0), Basic ($49/month), Enterprise ($199/month)
        9.  ✅ **Tenant Billing Isolation** - Complete billing separation per tenant with Stripe customer mapping
        10. ✅ **Plan Usage Analytics** - Usage summary endpoints and upgrade recommendations
        11. ✅ **Billing Event Audit Trail** - Complete logging of all billing events for compliance
        12. ✅ **Production-Ready Configuration** - Secure API key management and error handling
        13. ✅ **Enhanced Configurable Limits System** - Database-driven limit overrides with dual approval workflow:
            - Custom per-tenant limit overrides (users, documents, frameworks, storage)
            - Two-step approval process with different approvers required
            - Business justification and urgency levels for all requests
            - Temporary vs permanent overrides with expiration dates
            - Comprehensive email notification system for all approval stages
            - Full audit trail and administrative application controls
            - API endpoints for request submission, approval, and management
            - Integration with existing plan enforcement and usage tracking

*   **Story 0.6: Setup Document Storage (Azure Blob)**
    *   **Status:** Done
    *   **Description:** As a Developer, I need to configure the application to use Azure Blob Storage for all user-uploaded files, with a local mock (Azurite) for development.
    *   **AC:**
        1.  The Django storage backend is configured to use `azure-storage-blob`.
        2.  File uploads in the application are stored in Azure Blob Storage in production.
        3.  Files are stored in tenant-specific containers or paths for security.
        4.  The local `compose.yml` includes the Azurite service for local file handling.
    *   **What was achieved:**
        1.  ✅ **Custom Azure Blob Storage Backend** - Implemented `TenantAwareBlobStorage` with complete Azure Blob Storage integration
        2.  ✅ **Tenant Isolation** - Each tenant gets isolated container (`tenant-{slug}`) for complete data separation
        3.  ✅ **Fallback Storage System** - Graceful fallback to local storage when Azure is unavailable
        4.  ✅ **Document Management API** - Complete RESTful API for file upload, download, and management:
            - `POST /api/documents/` - Upload files with validation and metadata
            - `GET /api/documents/` - List tenant-specific documents
            - `GET /api/documents/{id}/download/` - Secure file download with audit logging
            - `GET /api/documents/{id}/access_logs/` - Access audit trail
            - `GET /api/documents/storage_info/` - Storage backend information
        5.  ✅ **File Validation** - Size limits (100MB), file type restrictions, security checks
        6.  ✅ **Audit Logging** - Document access tracking with IP, user agent, timestamps
        7.  ✅ **Production-Ready Configuration** - Azure Storage connection string setup for production deployment
        8.  ✅ **Azurite Integration** - Local development environment with Azure Storage emulator
        9.  ✅ **Multi-tenant Database Schema** - Document models with proper tenant isolation via django-tenants
        10. ✅ **Comprehensive Testing** - Verified file upload, storage, retrieval, and tenant isolation

*   **Story 0.7: Create CI/CD Pipeline (GitHub Actions)**
    *   **Status:** Done
    *   **Description:** As a Developer, I want a CI/CD pipeline that automatically runs tests, builds the Docker image, and deploys the application to Azure.
    *   **AC:**
        1.  A CI workflow runs on every push/pull request to the `main` branch.
        2.  The CI workflow runs all Django tests against a test database.
        3.  A CD workflow triggers on a merge to `main`.
        4.  The CD workflow builds and pushes the production Docker image to a container registry.
        5.  The CD workflow deploys the new image to Azure App Service.
    *   **What was achieved:**
        1.  ✅ **Comprehensive CI Pipeline** - Complete GitHub Actions workflow for continuous integration:
            - Backend testing with PostgreSQL, Redis, and Azurite services
            - Frontend testing with Node.js and npm
            - Code quality checks with Black, Flake8, and Django system checks
            - Coverage reporting with pytest-cov and Codecov integration
            - Multi-environment test configuration (test.py settings)
        2.  ✅ **Advanced CD Pipeline** - Production-ready continuous deployment workflow:
            - Multi-stage Docker builds with optimized production images
            - GitHub Container Registry integration with automated pushing
            - Staged deployment (staging → production) with approval gates
            - Database migration automation via Azure CLI
            - Health checks and smoke tests for deployment verification
            - Automatic rollback capabilities on deployment failure
        3.  ✅ **Security Integration** - Comprehensive security scanning throughout pipeline:
            - Dependency vulnerability scanning with Safety and npm audit
            - Static code analysis with Bandit and CodeQL
            - Container security scanning with Trivy
            - Secrets detection with TruffleHog
            - Dockerfile security linting with Hadolint
            - Infrastructure security with Checkov
        4.  ✅ **Production Infrastructure** - Complete production-ready configuration:
            - Multi-stage Dockerfile with security best practices
            - Non-root user execution and minimal attack surface
            - Health check endpoints (/health/, /health/ready/, /health/live/)
            - Startup scripts with automated migrations and initial data setup
            - Production settings with comprehensive security headers
        5.  ✅ **Quality Assurance** - Comprehensive testing and quality framework:
            - pytest configuration with fixtures and test utilities
            - Test database setup with tenant isolation
            - Integration tests for complete workflow validation
            - Code coverage requirements (70% minimum)
            - Automated dependency updates with Dependabot
        6.  ✅ **Development Workflow** - Professional development process:
            - Pull request templates with comprehensive checklists
            - Issue templates for bugs and feature requests
            - Branch protection setup guide with security requirements
            - Code owners configuration for review assignments
            - Automated security scanning on all PRs
        7.  ✅ **Deployment Automation** - Zero-downtime deployment capabilities:
            - Environment-specific configurations (staging/production)
            - Database backup before production deployments
            - Gradual rollout with health monitoring
            - Environment protection rules with manual approval gates
            - Comprehensive logging and monitoring setup
        8.  ✅ **Code Quality Standards** - Enforced coding standards and best practices:
            - Black code formatting with 100-character line length
            - Flake8 linting with Django-specific rules
            - Import sorting with isort
            - Type checking configuration with mypy
            - Security scanning with bandit for common vulnerabilities

*   **Story 0.8: Implement Enterprise SSO Integration**
    *   **Status:** Pending
    *   **Priority:** High for Enterprise Sales
    *   **Description:** As an Enterprise Customer, I want to use my company's SSO system (SAML/OAuth) to authenticate users so that we can maintain centralized identity management and comply with security policies.
    *   **AC:**
        1.  Support SAML 2.0 authentication with enterprise identity providers (Okta, Azure AD, etc.)
        2.  Support OAuth 2.0/OpenID Connect for modern identity providers (Google Workspace, Microsoft 365)
        3.  Per-tenant SSO configuration via admin interface with multiple provider support
        4.  Just-in-time (JIT) user provisioning with automatic account creation
        5.  Advanced role and attribute mapping from SSO providers to application roles
        6.  Fallback authentication allowing password login when SSO is unavailable
        7.  SSO-enforced login policies (disable password authentication for SSO-enabled tenants)
        8.  Comprehensive SSO audit logging and session management
        9.  Admin UI for tenant administrators to configure and manage SSO settings
        10. Support for SCIM provisioning and deprovisioning workflows
    *   **Technical Requirements:**
        - Multi-tenant SSO configuration storage
        - Integration with `django-saml2-auth` and `django-allauth`
        - Custom user provisioning and role mapping logic
        - SSO provider metadata management and validation
        - Session management across SSO and local authentication
        - Comprehensive error handling and fallback mechanisms
    *   **Enterprise Features:**
        - Multiple SSO providers per tenant (primary + backup)
        - Group-based role assignment and permissions mapping
        - Custom attribute mapping for user metadata
        - SSO connection testing and validation tools
        - Bulk user import/export capabilities
        - Integration with existing billing and limit enforcement systems

### EPIC 1: Certifications & Compliance Workflows

*Objective: Allow clients to manage compliance against various frameworks (ISO, NIST, etc.) by assessing controls and providing evidence.*

#### User Stories:

*   **Story 1.1: Implement Framework & Control Catalog**
    *   **Status:** Done
    *   **Description:** As an Admin, I want to import compliance frameworks (like ISO 27001) from a spreadsheet so that clients can assess themselves against them.
    *   **AC:**
        1.  Create Django models for `Framework`, `Clause`, and `Control`.
        2.  Build a management command to import these from a structured file (e.g., CSV, XLSX).
        3.  The imported frameworks are versioned.
    *   **What was achieved:**
        1.  ✅ Comprehensive Django models: `Framework`, `Clause`, `Control`, `ControlEvidence`, `FrameworkMapping`
        2.  ✅ Advanced framework features: versioning, lifecycle management, external references, change tracking
        3.  ✅ Management commands: `import_framework`, `export_framework`, `setup_frameworks`, `load_framework_fixtures`
        4.  ✅ Support for JSON/YAML import formats with comprehensive validation and error handling
        5.  ✅ Built-in framework fixtures: ISO 27001:2022, SOC 2 Type II, NIST CSF v1.1 with real-world clauses
        6.  ✅ Django Admin interface with advanced filtering, search, and relationship management
        7.  ✅ Full REST API with filtering, search, ordering, and framework-specific endpoints
        8.  ✅ Control lifecycle management: testing tracking, effectiveness ratings, evidence collection
        9.  ✅ Framework mapping system for cross-framework compliance analysis
        10. ✅ Comprehensive test suite covering models, API endpoints, and management commands
        11. ✅ Integration with GRC document templates and policy structures from existing documents

*   **Story 1.2: Create Control Assessments**
    *   **Status:** Pending
    *   **Description:** As a Compliance Manager, I want to view the controls for a framework and assess each one for my company.
    *   **AC:**
        1.  A `ControlAssessment` model links a `Tenant` to a `Control`.
        2.  On a UI, a user can mark a control as "Applicable" (Yes/No), set a status (e.g., "Pending", "In Progress", "Complete"), assign an owner, and set a due date.
        3.  All actions are saved to the database.

*   **Story 1.3: Manage Evidence for Assessments**
    *   **Status:** Pending
    *   **Description:** As a Compliance Manager, I want to upload documents as evidence for a control assessment and link to existing documents.
    *   **AC:**
        1.  An `Evidence` model links an uploaded file to a `ControlAssessment`.
        2.  Users can upload files (PDF, DOCX, images) on the assessment page.
        3.  Files are securely stored in the tenant's Azure Blob Storage container.
        4.  Users can view and download previously uploaded evidence.

*   **Story 1.4: Implement Automated Reminders**
    *   **Status:** Pending
    *   **Description:** As a Control Owner, I want to receive an email notification when my assigned task is due soon or has expired.
    *   **AC:**
        1.  A scheduled Celery task runs daily to check for due dates.
        2.  Emails are sent 7 days before the due date and on the day it is due.
        3.  Email content clearly states which control assessment requires attention.

### EPIC 2: Risk Management

*Objective: Provide a module for clients to identify, assess, and track risks to their organization.*

#### User Stories:

*   **Story 2.1: Develop Risk Register**
    *   **Status:** Pending
    *   **Description:** As a Risk Manager, I want a risk register where I can add, view, and edit risks.
    *   **AC:**
        1.  A `Risk` model is created with fields for title, description, owner, impact, likelihood, etc.
        2.  A UI allows for CRUD (Create, Read, Update, Delete) operations on risks.
        3.  The risk rating is automatically calculated (Impact x Likelihood) based on a configurable matrix.

*   **Story 2.2: Implement Risk Treatment & Notifications**
    *   **Status:** Pending
    *   **Description:** As a Risk Owner, I want to define mitigation plans for a risk and receive notifications for overdue actions.
    *   **AC:**
        1.  A `RiskAction` model is linked to a `Risk` with a due date and owner.
        2.  A daily scheduled task sends email reminders for overdue risk actions.
        3.  Users can upload evidence to show a risk has been remediated.

### EPIC 3: Vendor Management

*Objective: Enable clients to track their vendors, manage associated risks, and monitor key dates.*

#### User Stories:

*   **Story 3.1: Create Vendor Profiles**
    *   **Status:** Pending
    *   **Description:** As a Procurement Manager, I want to create and manage a profile for each vendor, including contact details and services provided.
    *   **AC:**
        1.  A `Vendor` model is created to store vendor information.
        2.  A UI allows for CRUD operations on vendor profiles.

*   **Story 3.2: Track Vendor Activities & Renewals**
    *   **Status:** Pending
    *   **Description:** As a Procurement Manager, I want to track important dates for each vendor, such as contract renewals and security reviews, and receive reminders.
    *   **AC:**
        1.  A `VendorTask` model is created with a type and due date.
        2.  A daily scheduled task sends email reminders for upcoming vendor-related due dates.

### EPIC 4: Policies & Training

*Objective: Create a central repository for company policies and deliver security awareness training.*

#### User Stories:

*   **Story 4.1: Implement Policy Repository**
    *   **Status:** Pending
    *   **Description:** As a Compliance Manager, I want to upload company policies to a central repository where they can be versioned and managed.
    *   **AC:**
        1.  A `Policy` model is created with versioning support.
        2.  Admins can upload new policy documents (PDF, DOCX).

*   **Story 4.2: Track Policy Acknowledgement**
    *   **Status:** Pending
    *   **Description:** As a Compliance Manager, I want to send policies to staff and track who has read and acknowledged them.
    *   **AC:**
        1.  An `Acknowledgement` model links a `User` to a `PolicyVersion`.
        2.  A UI allows staff to view a policy and click an "Acknowledge" button.
        3.  A dashboard shows the acknowledgment status for each policy.
        4.  Scheduled reminders are sent to users who have not acknowledged a required policy.

*   **Story 4.3: Implement Security Awareness & Training Modules**
    *   **Status:** Pending
    *   **Description:** As an Admin, I want to schedule security awareness materials to be sent via email and provide a module for video training.
    *   **AC:**
        1.  A UI allows an admin to schedule recurring emails with awareness content.
        2.  A separate page embeds training videos from the specified provider (Synthesia.io).

### EPIC 5: Advanced Features & UI/UX

*Objective: Enhance the application with advanced functionality and a beautiful, intuitive user interface.*

#### User Stories:

*   **Story 5.1: Implement Inline Document Editing (ONLYOFFICE)**
    *   **Status:** Pending
    *   **Description:** As a User, I want to edit uploaded Word and Excel documents directly within the application.
    *   **AC:**
        1.  Integrate the ONLYOFFICE Document Server.
        2.  When a user clicks "Edit" on a compatible document, it opens in the ONLYOFFICE editor.
        3.  Changes are saved back to Azure Blob Storage as a new version of the file.

*   **Story 5.2: Implement Vulnerability Scanning (Ingest-First)**
    *   **Status:** Pending
    *   **Description:** As a Security Analyst, I want to upload vulnerability scan reports (e.g., from OpenVAS) and have the findings imported into the system.
    *   **AC:**
        1.  Create models for `Asset` and `Finding`.
        2.  A parser is built to ingest XML/JSON reports from a chosen scanner.
        3.  A UI displays the imported findings, linked to assets.

*   **Story 5.3: Build Analytics & Reporting**
    *   **Status:** Pending
    *   **Description:** As a Manager, I want to view dashboards with key metrics and be able to download reports in PDF or spreadsheet format.
    *   **AC:**
        1.  Dashboards are created to visualize compliance status, risk posture, etc.
        2.  An async export feature allows users to download data from any module.
        3.  Exports are generated in the background by a Celery task.

*   **Story 5.4: Implement Beautiful UI Theme**
    *   **Status:** Pending
    *   **Description:** As a User, I want the application to have a clean, modern, and professional user interface as defined in the design blueprint.
    *   **AC:**
        1.  Implement the Ant Design theme with the specified color palette, typography, and spacing.
        2.  Build reusable, polished components for KPI cards, status tags, empty states, etc.
        3.  Implement a light/dark mode toggle.
