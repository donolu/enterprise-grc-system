# ADR-0004: Azure Blob Storage with Tenant Isolation

## Status
Accepted

## Context
Story 0.6 required implementing secure document storage for the multi-tenant GRC platform. The system needed:

- Cloud-based storage solution for scalability and reliability
- Tenant isolation to ensure data security between organizations
- Local development environment support
- Fallback mechanisms for high availability
- Audit logging for compliance requirements
- Integration with existing Django multi-tenant architecture

## Decision
We have implemented Azure Blob Storage as the primary document storage solution with the following architectural decisions:

### 1. Custom Storage Backend
Created `TenantAwareBlobStorage` class extending Django's Storage interface:
- Implements automatic tenant isolation using container naming: `tenant-{slug}`
- Provides fallback to local filesystem when Azure is unavailable
- Handles connection string management and blob client initialization
- Supports standard Django file operations with Azure-specific optimizations

### 2. Tenant Container Strategy
Each tenant gets its own Azure Blob container:
- Container naming: `tenant-{tenant_slug}` (e.g., `tenant-shared`)
- Automatic container creation on first use
- Date-based file organization: `document/YYYY/MM/DD/filename`
- Prevents cross-tenant data access at the storage level

### 3. Local Development with Azurite
Configured Azurite (Azure Storage Emulator) for development:
- Full Azure Storage API compatibility
- Docker-based deployment in compose.yml
- Host binding configuration: `--blobHost 0.0.0.0` for inter-container communication
- Command array format to ensure proper networking

### 4. Fallback Storage Mechanism
Implemented dual-storage strategy:
- Primary: Azure Blob Storage (production) / Azurite (development)
- Fallback: Local filesystem storage when Azure unavailable
- Automatic detection and switching based on connectivity
- Graceful degradation without service interruption

### 5. Document Management API
Created comprehensive RESTful API:
- `POST /api/documents/` - Upload with automatic metadata extraction
- `GET /api/documents/` - List with filtering and pagination
- `GET /api/documents/{id}/download/` - Secure download with audit logging
- `DELETE /api/documents/{id}/` - Secure deletion
- `GET /api/storage-info/` - Storage backend status and diagnostics

### 6. Security and Audit
Implemented security controls:
- User-based access control through Django permissions
- Audit logging via DocumentAccess model
- File size validation and type restrictions
- Secure URL generation with time-limited access

## Alternatives Considered

### AWS S3
- **Pros**: Mature ecosystem, extensive documentation
- **Cons**: Vendor lock-in, additional AWS dependencies
- **Rejected**: Project already uses Azure services

### Local File Storage Only
- **Pros**: Simple implementation, no external dependencies
- **Cons**: Poor scalability, backup complexity, no CDN capabilities
- **Rejected**: Insufficient for production multi-tenant requirements

### Database BLOB Storage
- **Pros**: Transactional consistency, simple backup
- **Cons**: Database bloat, poor performance for large files
- **Rejected**: Not suitable for document-heavy workloads

## Consequences

### Positive
- **Scalability**: Virtually unlimited storage capacity
- **Security**: Strong tenant isolation at infrastructure level
- **Reliability**: Azure's 99.9% uptime SLA
- **Development Experience**: Azurite enables full local testing
- **Compliance**: Built-in audit logging for regulatory requirements
- **Performance**: CDN-ready URLs for global document delivery

### Negative
- **Complexity**: Additional configuration and monitoring requirements
- **Cost**: Usage-based pricing model requires monitoring
- **Dependencies**: External service dependency (mitigated by fallback)
- **Development Setup**: Requires Azurite container for local development

### Risks and Mitigations
- **Azure Service Outage**: Mitigated by fallback to local storage
- **Cost Overruns**: Mitigated by monitoring and storage lifecycle policies
- **Data Migration**: Future migration complexity due to blob storage format
- **Container Naming Conflicts**: Prevented by tenant slug validation

## Implementation Details

### Configuration
```python
# Django settings
DEFAULT_FILE_STORAGE = 'core.storage.TenantAwareBlobStorage'
AZURE_STORAGE_CONNECTION_STRING = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
```

### Docker Configuration
```yaml
azurite:
  image: mcr.microsoft.com/azure-storage/azurite:latest
  command: ["azurite", "--silent", "--location", "/data", "--blobHost", "0.0.0.0"]
  ports: ["10000:10000","10001:10001","10002:10002"]
```

### File Upload Path
```python
def tenant_file_upload_path(instance, filename):
    return f"document/{timezone.now().strftime('%Y/%m/%d')}/{filename}"
```

## Success Metrics
- ✅ Successful file upload and download operations
- ✅ Tenant isolation verified (separate containers)
- ✅ Fallback mechanism tested and functional
- ✅ API endpoints operational with proper authentication
- ✅ Audit logging capturing all document access
- ✅ Local development environment fully functional

## Future Considerations
- Implement Azure CDN for global document delivery
- Add lifecycle policies for automated document archival
- Consider Azure AD integration for enhanced security
- Implement document versioning and backup strategies
- Add storage usage monitoring and alerting

## References
- Story 0.6: Document Storage Implementation
- Azure Blob Storage Documentation
- Django File Storage Documentation
- Azurite Local Development Setup