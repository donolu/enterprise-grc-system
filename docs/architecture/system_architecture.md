# System Architecture

## 1. Overview
This document outlines the technical architecture for the multi-tenant GRC SaaS platform. The system is designed as a modern web application with a decoupled frontend and backend, built on a scalable, cloud-native foundation on Microsoft Azure.

## 2. Core Components
The architecture is composed of the following key services and technologies:

*   **Backend (API):**
    *   **Framework:** Django + Django REST Framework (DRF)
    *   **Language:** Python
    *   **Function:** A robust REST API that handles all business logic, including authentication, data processing, and GRC workflows.

*   **Frontend (UI):**
    *   **Framework:** Next.js + React
    *   **Language:** TypeScript
    *   **UI Library:** Ant Design
    *   **Function:** A responsive Single-Page Application (SPA) that provides a rich, interactive user experience.

*   **Database:**
    *   **System:** PostgreSQL
    *   **Multi-Tenancy:** Implemented via `django-tenants`, which provides strong data isolation by creating a separate database schema for each client tenant.

*   **Asynchronous Task Processing:**
    *   **System:** Celery (with Celery Beat for scheduling)
    *   **Broker/Backend:** Redis
    *   **Function:** Executes all background jobs, such as sending email notifications, generating reports, and running vulnerability scan ingestions, ensuring the main application remains fast and responsive.

*   **Document Storage:**
    *   **Service:** Azure Blob Storage
    *   **Function:** Securely stores all user-uploaded files and evidence. Files are organized by tenant to enforce access control.

*   **Inline Document Editing:**
    *   **Service:** ONLYOFFICE Document Server
    *   **Function:** Provides in-browser editing capabilities for DOCX and XLSX files, with changes saved back to Azure Blob Storage.

## 3. Component Interaction Diagram (C4 Model)

```plantuml
@startuml C4_Component_Diagram
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Component.puml

LAYOUT_WITH_LEGEND()

Person(user, "GRC User", "A client user managing compliance, risk, etc.")

System_Boundary(c1, "GRC SaaS Platform") {
    Component(frontend, "Next.js Frontend", "Next.js, React, Ant Design", "Provides the user interface")
    Component(backend, "Django API", "Django, DRF", "Handles all business logic and data orchestration")
    Component(celery_worker, "Celery Worker", "Celery, Python", "Executes async tasks like emails and reports")
    ComponentDb(db, "PostgreSQL DB", "PostgreSQL", "Stores all application data with schema-per-tenant isolation")
    ComponentQueue(redis, "Redis", "Redis", "Message broker for Celery and caching layer")
}

System_Ext(onlyoffice, "ONLYOFFICE", "Document editing service")
System_Ext(azure_blob, "Azure Blob Storage", "Stores all uploaded documents and evidence")
System_Ext(payment_gw, "Stripe", "Handles subscriptions and billing")
System_Ext(email_svc, "Azure Communication Services / SendGrid", "Sends all transactional emails")

Rel(user, frontend, "Uses", "HTTPS")

Rel(frontend, backend, "Makes API calls to", "HTTPS/JSON")

Rel(backend, db, "Reads/Writes", "SQL")
Rel(backend, redis, "Queues tasks for", "Redis Protocol")
Rel(backend, azure_blob, "Reads/Writes files to", "HTTPS")
Rel(backend, payment_gw, "Manages subscriptions via", "API")
Rel(backend, email_svc, "Sends emails via", "SMTP/API")
Rel(backend, onlyoffice, "Generates signed URLs for", "API")

Rel(celery_worker, db, "Reads/Writes", "SQL")
Rel_R(celery_worker, redis, "Pulls tasks from")
Rel(celery_worker, email_svc, "Sends emails via", "SMTP/API")

Rel(frontend, onlyoffice, "Embeds editor for", "HTTPS")
Rel(frontend, azure_blob, "Uploads files directly to", "HTTPS/SAS")

@enduml
```

## 4. Production Architecture (Azure)
*   **Compute:** Azure App Service or Azure Kubernetes Service (AKS) will host the containerized application services (Django, Next.js, Celery).
*   **Database:** Azure Database for PostgreSQL (Flexible Server) will be used for the primary database.
*   **Cache/Broker:** Azure Cache for Redis will serve as the Celery broker and application cache.
*   **Storage:** Azure Blob Storage for persistent, scalable file storage.
*   **Email:** Azure Communication Services or SendGrid for reliable email delivery.
*   **Monitoring:** Azure Monitor and Application Insights for performance and error tracking.
*   **CI/CD:** GitHub Actions will be used to build, test, and deploy the application automatically.