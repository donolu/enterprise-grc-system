# Deployment Options

The application is packaged as one production Docker image and configured through environment variables. Azure remains supported, but no runtime code path should require Azure-specific services.

## Common Runtime Contract

Every production target needs:

- `SECRET_KEY`
- `DATABASE_URL`
- `DIRECT_DATABASE_URL` when migrations must bypass a pooler
- `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- `PUBLIC_HOSTNAME`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`
- email provider settings
- Stripe settings when billing is enabled
- one storage backend configuration

Use [deploy/production.env.example](../deploy/production.env.example) as the canonical variable list.

## Storage

Set `STORAGE_BACKEND` to one of:

- `azure` for Azure Blob Storage using `AZURE_STORAGE_CONNECTION_STRING`
- `s3` for AWS S3, DigitalOcean Spaces, Cloudflare R2 or MinIO using the `OBJECT_STORAGE_*` variables
- `filesystem` for self-hosted single-node deployments with a persistent media volume

Tenant isolation is preserved in all modes. Azure uses one tenant container per tenant. S3-compatible and filesystem storage use tenant prefixes such as `tenant-acme/...`.

## Container Image

The CD workflow publishes the production image to GHCR:

```text
ghcr.io/donolu/grc-platform:<tag>
```

Use an immutable `sha-*` tag for production releases. `latest` is acceptable for disposable staging environments only.

## Self-hosted Docker Compose

Use [deploy/docker-compose.production.yml](../deploy/docker-compose.production.yml) with an env file based on `deploy/production.env.example`.

```bash
docker compose --env-file deploy/production.env -f deploy/docker-compose.production.yml up -d
docker compose --env-file deploy/production.env -f deploy/docker-compose.production.yml exec web python manage.py migrate_schemas --shared
docker compose --env-file deploy/production.env -f deploy/docker-compose.production.yml exec web python manage.py migrate_schemas
```

For a single host, start with `STORAGE_BACKEND=filesystem` and keep the `media` volume backed up. For multi-host deployments, use `STORAGE_BACKEND=s3`.

## Azure

Azure App Service and slot swaps remain supported through the existing CD workflow and [deploy/docker-compose.webapp.yml](../deploy/docker-compose.webapp.yml).

Azure-specific configuration is now limited to deploy-time secrets and optional Azure Blob storage:

- `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`
- `AZURE_RESOURCE_GROUP`, `AZURE_WEBAPP_NAME`, `AZURE_SLOT_STAGING`
- `STORAGE_BACKEND=azure`
- `AZURE_STORAGE_CONNECTION_STRING`

## Render

Use [deploy/render.yaml](../deploy/render.yaml) as the Blueprint. Fill all `sync: false` values in the Render dashboard before first deploy.

Render should use:

- managed Postgres for `DATABASE_URL`
- managed Redis for Celery and cache
- `STORAGE_BACKEND=s3` with an external S3-compatible bucket
- `PUBLIC_HOSTNAME` and `RENDER_EXTERNAL_HOSTNAME` from the web service host

## DigitalOcean

Use [deploy/digitalocean-app.yaml](../deploy/digitalocean-app.yaml) as the App Platform starter spec.

DigitalOcean Spaces works through:

```text
STORAGE_BACKEND=s3
OBJECT_STORAGE_ENDPOINT_URL=https://<region>.digitaloceanspaces.com
OBJECT_STORAGE_REGION=<region>
OBJECT_STORAGE_BUCKET=<bucket>
```

## AWS

Use [deploy/aws-ecs-task-definition.json](../deploy/aws-ecs-task-definition.json) as the ECS/Fargate starting point.

Recommended managed services:

- RDS PostgreSQL
- ElastiCache Redis
- S3 for object storage
- Systems Manager Parameter Store or Secrets Manager for secrets
- CloudWatch Logs for application output

Run migrations as a one-off ECS task using the same image and direct database URL.

## Operational Notes

- Keep migrations on the direct database connection when a pooler is present.
- Keep object storage private unless the download flow deliberately issues signed URLs.
- Do not put provider-specific credentials in the image; all secrets must be injected by the platform.
- Keep the Azure Terraform module as one option, not as the authoritative runtime contract.
