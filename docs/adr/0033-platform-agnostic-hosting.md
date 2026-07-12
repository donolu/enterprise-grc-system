# ADR-0033: Platform-agnostic hosting

## Status
Proposed

## Context
Deployment is currently tied to Azure: the app runs on Azure App Service with slot swaps, stores media in Azure Blob Storage (ADR-0004), and the CD workflow is Azure-specific. The application is already containerised and mostly configured through environment variables, so most of the platform coupling is at the edges (storage and the deploy pipeline) rather than in the code. To keep commercial and operational flexibility, hosting should be portable enough to move to Render, DigitalOcean, AWS, or self-hosting without code changes.

## Decision
Treat the container image as the portable unit and push all platform specifics to configuration.

- **12-factor configuration.** Everything that varies by environment (database, cache/broker, storage, secrets, allowed hosts, CORS) is read from environment variables, so the same image boots on any platform.
- **Storage backend by configuration.** Select the django-storages backend from the environment (Azure Blob, S3, DigitalOcean Spaces, Cloudflare R2, GCS) through an S3-compatible endpoint, rather than hardcoding Azure Blob. Tenant isolation of stored objects is preserved across backends.
- **Neutral image registry.** Publish the production image to GHCR so any platform can pull it. Azure remains a deploy target, not the only one.
- **Portable deploy manifests and docs.** Provide a production compose file plus platform blueprints (a Render Blueprint, a DigitalOcean App Platform spec, and an AWS ECS task definition) and a deployment-options guide covering Azure, Render, DigitalOcean, AWS, and self-hosting. Migrations run against the direct database URL on every platform.

## Consequences
- Freedom to move providers and real negotiating leverage on hosting cost; no single-vendor lock-in.
- A small abstraction cost on storage configuration and a few more deploy manifests to maintain.
- CI gains a step to publish the image to GHCR.

## Alternatives considered
- Stay Azure-only: lowest effort today, but locks the product to one provider and its pricing.
- Full infrastructure-as-code (Terraform) now: more portable still, but premature for the current team size and scale; the blueprint-per-platform approach is lighter and sufficient.

## References
- Issue #92; ADR-0004 (Azure Blob storage with tenant isolation), ADR-0007 (CI/CD pipeline).
