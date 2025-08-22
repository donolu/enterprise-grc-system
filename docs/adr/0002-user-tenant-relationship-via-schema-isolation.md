# ADR 0002: User-Tenant Relationship via Schema Isolation

*   **Status:** Decided
*   **Date:** 2025-08-22

## Context

Story 0.3 required implementing user authentication with users linked to tenants. The original acceptance criteria specified "The `core.User` model is linked to a `Tenant`" which typically implies a foreign key relationship. However, with django-tenants implementation completed in Story 0.2, we needed to decide how to handle the user-tenant relationship in a schema-isolated multi-tenant architecture.

## Decision

We decided to implement user-tenant relationship through **schema isolation** rather than explicit foreign key relationships, leveraging django-tenants' built-in tenant isolation mechanism.

### Approach Taken:

1. **Schema-Based Isolation:** Users exist within tenant schemas, automatically providing tenant association
2. **No Foreign Key:** Removed explicit `tenant` foreign key from User model  
3. **Implicit Association:** User-tenant relationship is implicit through the schema they exist in
4. **Automatic Isolation:** Django-tenants middleware handles tenant resolution and data isolation

## Rationale

### Advantages of Schema Isolation Approach:

1. **Stronger Security:** Complete data isolation at the database level
2. **Better Performance:** No need for tenant filtering in queries
3. **Simplified Queries:** All model queries automatically scoped to current tenant
4. **Django-Tenants Best Practice:** Aligns with recommended django-tenants architecture
5. **Automatic Compliance:** Ensures users cannot accidentally access cross-tenant data

### Alternative Considered:

- **Foreign Key Approach:** User model with `tenant_id` foreign key
- **Rejected because:** 
  - Requires manual tenant filtering on every query
  - Risk of data leakage if filtering is missed
  - Performance overhead of additional JOIN conditions
  - Conflicts with django-tenants schema isolation model

## Consequences

### Positive:
- ✅ Complete tenant isolation guaranteed at database level
- ✅ Simplified application code - no manual tenant filtering needed
- ✅ Better security posture
- ✅ Scalable architecture that supports many tenants

### Trade-offs:
- 📝 Cross-tenant operations require special handling (if needed in future)
- 📝 Tenant identification requires subdomain or header-based routing
- 📝 Slightly different from traditional FK-based multi-tenancy

## Implementation Details

- User model simplified to extend AbstractUser without tenant FK
- Tenant resolution handled by `django_tenants.middleware.main.TenantMainMiddleware`
- Users created within specific tenant schemas via management commands
- Authentication endpoints work within tenant context automatically

## Verification

Tested and verified:
- ✅ Users isolated by tenant (same username can exist in multiple tenants)
- ✅ No cross-tenant data access possible
- ✅ Authentication works correctly within tenant context
- ✅ Registration creates users in correct tenant schema

This approach successfully meets the intent of AC #5 ("User model linked to Tenant") through architectural design rather than explicit data modeling.