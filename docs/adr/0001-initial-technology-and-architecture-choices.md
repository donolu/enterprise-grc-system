# ADR 0001: Initial Technology and Architecture Choices

*   **Status:** Decided
*   **Date:** 2025-08-21

## Context

We need to build a multi-tenant Information Security GRC SaaS application. The requirements include complex workflows, compliance management, risk assessment, document handling, user management, and billing. The application must be scalable, secure, and maintainable, with a modern, professional user interface. It will be deployed on Microsoft Azure.

## Decision

We have decided to adopt the comprehensive technical blueprint provided, which outlines a clear and robust architecture. The key choices are:

1.  **Backend:** Django + Django REST Framework (DRF) for a powerful and scalable API.
2.  **Frontend:** Next.js (React) + TypeScript + Ant Design for a modern, interactive, and beautiful user interface.
3.  **Database:** PostgreSQL, which is robust and well-supported by Django.
4.  **Multi-Tenancy:** `django-tenants` (schema-per-tenant model) to ensure strong data isolation and security between clients.
5.  **Deployment & Infrastructure:** A container-based approach using Docker, with production infrastructure managed on Azure (App Service, PostgreSQL, Blob Storage, Redis) via Terraform (Infrastructure as Code).
6.  **Local Development:** A full local simulation of the Azure environment using Docker Compose, including services like Azurite (for Blob Storage) and MailHog (for email), to ensure high-fidelity local testing.
7.  **Asynchronous Tasks:** Celery and Redis to manage background jobs like sending email reminders and generating reports.
8.  **Inline Document Editing:** ONLYOFFICE Document Server, integrated via its API and run as a Docker container.

## Consequences

*   **Pros:**
    *   This stack is modern, well-supported, and widely used for building scalable web applications.
    *   The separation of frontend and backend allows for independent development and scaling.
    *   Using schema-per-tenant provides the strongest level of data isolation.
    *   Infrastructure as Code (Terraform) and CI/CD (GitHub Actions) will lead to reliable and repeatable deployments.
    *   The local development environment closely mirrors production, reducing deployment-related bugs.
*   **Cons:**
    *   The architecture is complex and involves many moving parts, requiring careful orchestration.
    *   Reliance on several third-party services (Stripe, ONLYOFFICE, Azure) creates external dependencies.
