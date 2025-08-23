# ADR-0014: Comprehensive API Documentation with drf-spectacular

## Status
Accepted

## Context
Following the successful implementation of Stories 1.1-1.5 (Framework Management, Control Assessments, Evidence Management, Assessment Reporting, and Automated Reminders), the GRC SaaS platform required comprehensive API documentation to support frontend development, third-party integrations, and developer adoption. The API documentation needed to be interactive, maintainable, and provide clear guidance for complex operations like bulk uploads, assessment workflows, and tenant-aware operations.

### Problem Statement
The GRC SaaS platform needed professional API documentation that would:
- Provide interactive documentation for 50+ API endpoints across 8 modules
- Document complex workflows (assessment lifecycle, evidence management, report generation)
- Support bulk operations and file upload specifications
- Maintain tenant-aware security context documentation
- Auto-generate from code to ensure accuracy and maintainability
- Support multiple documentation formats (Swagger UI, ReDoc)
- Include comprehensive examples and error handling guidance
- Facilitate frontend development and third-party integrations

### Existing Infrastructure Analysis
- ✅ **Django REST Framework**: Established ViewSet architecture with comprehensive serializers
- ✅ **Multi-module Architecture**: Organized codebase across catalogs, authn, exports, billing, core modules
- ✅ **Complex Operations**: Bulk operations, file uploads, async report generation already implemented
- ✅ **Security Infrastructure**: Session authentication and tenant isolation patterns established
- ✅ **Comprehensive Serializers**: Rich serializer classes with detailed field definitions
- ✅ **Error Handling**: Consistent error response patterns across all endpoints

## Decision
We implemented comprehensive API documentation using drf-spectacular (OpenAPI 3.0) with interactive interfaces, detailed endpoint documentation, and comprehensive examples while maintaining consistency with established architectural patterns and ensuring documentation stays synchronized with code changes.

### Key Architecture Decisions

#### 1. drf-spectacular as Documentation Engine
```python
SPECTACULAR_SETTINGS = {
    "TITLE": "GRC SaaS API",
    "DESCRIPTION": """
    Comprehensive API for Governance, Risk, and Compliance (GRC) management.
    
    This API provides complete functionality for compliance framework management,
    control assessments, evidence collection, reporting, and automated reminders.
    """,
    "VERSION": "1.0.0",
    "OAS_VERSION": "3.0.3",
    "USE_SESSION_AUTH": True,
    "SCHEMA_PATH_PREFIX": "/api/",
    "COMPONENT_SPLIT_REQUEST": True,
}
```

**Rationale**: drf-spectacular provides automatic OpenAPI 3.0 schema generation from Django REST Framework code, ensuring documentation stays synchronized with implementation while supporting modern interactive documentation interfaces.

#### 2. Comprehensive ViewSet Documentation Architecture
```python
@extend_schema_view(
    list=extend_schema(
        summary="List control assessments",
        description="Retrieve a paginated list of control assessments with comprehensive filtering...",
        parameters=[
            OpenApiParameter(
                name='framework',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by framework ID'
            ),
            # ... additional parameters
        ],
        examples=[
            OpenApiExample(
                'My overdue assessments',
                summary='Get current user\'s overdue assessments',
                value='?my_assignments=true&overdue=true'
            ),
        ],
        tags=['Assessments'],
    ),
    # ... additional CRUD operations
)
class ControlAssessmentViewSet(viewsets.ModelViewSet):
    """
    **Control Assessment Management**
    
    This ViewSet provides comprehensive management of control assessments including:
    - Full assessment lifecycle management (creation, assignment, completion)
    - Evidence management and linking capabilities
    - Status tracking and progress monitoring
    """
```

**Rationale**: Decorator-based documentation approach allows for detailed specification of each endpoint while keeping documentation close to implementation code.

#### 3. Multi-Interface Documentation Strategy
```python
urlpatterns = [
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
```

**Rationale**: Multiple documentation interfaces (Swagger UI for interactive testing, ReDoc for comprehensive reading) serve different use cases and developer preferences.

#### 4. Comprehensive Response Documentation
```python
@extend_schema(
    summary="Upload evidence to assessment",
    description="Upload a file as evidence and link it directly to this assessment...",
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {
                'file': {'type': 'string', 'format': 'binary'},
                'title': {'type': 'string', 'description': 'Document title'},
                'evidence_type': {'type': 'string', 'description': 'Evidence type'},
            }
        }
    },
    responses={
        201: OpenApiResponse(
            description='Evidence uploaded and linked successfully',
            examples=[
                OpenApiExample(
                    'Successful Upload',
                    value={
                        'message': 'Evidence uploaded and linked to assessment successfully',
                        'document': {'id': 123, 'title': 'Network Security Policy.pdf'},
                        'evidence': {'id': 456, 'title': 'Network Security Policy Evidence'},
                    }
                ),
            ]
        ),
        400: OpenApiResponse(description='Bad request - file missing or invalid data'),
    },
)
```

**Rationale**: Detailed response documentation with real examples helps developers understand expected data structures and handle error cases properly.

#### 5. Tag-Based API Organization
```python
"TAGS": [
    {"name": "Authentication", "description": "User authentication and session management"},
    {"name": "Frameworks", "description": "Compliance framework management (ISO 27001, NIST CSF, SOC 2, etc.)"},
    {"name": "Assessments", "description": "Control assessment workflow and lifecycle management"},
    {"name": "Evidence", "description": "Evidence collection, management, and linking"},
    {"name": "Reports", "description": "Assessment reporting and PDF generation"},
    {"name": "Documents", "description": "File upload and document management"},
    {"name": "Billing", "description": "Subscription and billing management"}
],
```

**Rationale**: Logical grouping of endpoints by functional area improves navigation and understanding of the API structure.

### Documentation Coverage Implementation

#### 1. Core Catalog Management (catalogs/views.py)
- **FrameworkViewSet**: Complete CRUD operations for compliance frameworks
  - Framework listing with filtering by type, status, mandatory flag
  - Framework statistics with clause counts and control distribution
  - Related data access (clauses, controls, statistics)
- **ControlAssessmentViewSet**: Comprehensive assessment lifecycle management
  - Assessment creation, assignment, and status tracking
  - Evidence upload and linking with file management
  - Bulk operations for framework-wide assessment creation
  - Progress reporting with comprehensive analytics

#### 2. Authentication and Security (authn/views.py)
- **User Registration and Login**: Account creation and authentication
- **Two-Factor Authentication**: Email, TOTP, and push notification support
- **Session Management**: Login, logout, and profile management
- **Password Management**: Secure password change functionality

#### 3. Document Management (core/views.py)
- **File Upload and Storage**: Azure Blob Storage integration with tenant isolation
- **Plan-Based Limits**: Document quota enforcement based on subscription tier
- **Access Control**: Secure download with audit logging
- **Storage Information**: Debugging and configuration endpoints

#### 4. Report Generation (exports/views.py)
- **Async Report Generation**: PDF creation with status tracking
- **Report Configuration**: Framework and assessment selection options
- **Download Management**: Secure file access and URL generation
- **Quick Generation**: Single-operation report creation and processing

#### 5. Billing and Subscriptions (billing/views.py)
- **Plan Management**: Subscription tier information and features
- **Payment Processing**: Stripe integration for secure transactions
- **Subscription Management**: Upgrade, downgrade, and cancellation
- **Billing Portal**: Self-service billing history and invoice access

### API Documentation Features

#### 1. Interactive Documentation
- **Swagger UI**: Interactive API testing interface with request/response examples
- **ReDoc**: Comprehensive API documentation with detailed descriptions
- **Try It Out**: Direct API testing from documentation interface
- **Authentication Integration**: Session-based auth testing support

#### 2. Comprehensive Examples
- **Request Examples**: Real-world usage patterns for complex operations
- **Response Examples**: Expected data structures with actual values
- **Error Examples**: Common error scenarios with proper handling guidance
- **Workflow Examples**: Multi-step process documentation (assessment lifecycle)

#### 3. Parameter Documentation
- **Query Parameters**: Filtering, searching, and ordering options
- **Path Parameters**: Resource identification and navigation
- **Request Bodies**: JSON and multipart form data specifications
- **File Uploads**: Binary data handling and metadata requirements

#### 4. Security Documentation
- **Authentication Methods**: Session-based authentication requirements
- **Tenant Isolation**: Data scoping and access control explanation
- **Permission Model**: User-based and resource-based access control
- **Security Schemes**: OpenAPI security definition implementation

## Implementation Details

### Database Schema Impact
No database schema changes required - documentation is generated from existing models and serializers.

### API Endpoint Structure
```
/api/schema/          # OpenAPI 3.0 schema JSON/YAML
/api/docs/           # Interactive Swagger UI documentation
/api/redoc/          # Comprehensive ReDoc documentation interface
```

### Configuration Architecture
```python
# Enhanced SPECTACULAR_SETTINGS configuration
SPECTACULAR_SETTINGS = {
    # Core API metadata
    "TITLE": "GRC SaaS API",
    "VERSION": "1.0.0",
    "DESCRIPTION": "Comprehensive GRC management API...",
    
    # OpenAPI specification
    "OAS_VERSION": "3.0.3",
    "USE_SESSION_AUTH": True,
    "SCHEMA_PATH_PREFIX": "/api/",
    
    # Documentation enhancement
    "COMPONENT_SPLIT_REQUEST": True,
    "SORT_OPERATIONS": False,
    "SERVE_INCLUDE_SCHEMA": False,
    
    # Security schemes
    "SECURITY": [{"SessionAuth": []}],
    
    # Endpoint organization
    "TAGS": [/* comprehensive tag definitions */],
    
    # Error handling
    "DEFAULT_ERROR_RESPONSE_SCHEMA": "drf_spectacular.openapi.ErrorResponseSerializer",
}
```

### Performance Optimization
- **Schema Caching**: Generated schema cached for performance
- **Lazy Loading**: Documentation interfaces load on demand
- **Efficient Serialization**: Optimized schema generation from serializers
- **Static Asset Serving**: Documentation UI assets served efficiently

### Security Implementation
- **Access Control**: Documentation respects authentication requirements
- **Schema Security**: Sensitive information filtered from public schema
- **Tenant Isolation**: Documentation explains multi-tenant data scoping
- **Example Sanitization**: No real credentials or sensitive data in examples

## Alternatives Considered

### 1. Manual Documentation (Rejected)
**Rejected**: Manual documentation becomes outdated quickly and requires significant maintenance overhead. Code-generated documentation ensures accuracy.

### 2. Django REST Swagger (Rejected)
**Rejected**: Django REST Swagger is deprecated and lacks modern OpenAPI 3.0 features. drf-spectacular is the recommended successor.

### 3. External Documentation Tools (Rejected)
**Rejected**: External tools like Postman or Insomnia would require duplicate maintenance and wouldn't stay synchronized with code changes.

### 4. Minimal Documentation (Rejected)
**Rejected**: Given the complexity of the GRC domain and the number of endpoints, comprehensive documentation is essential for adoption and integration.

### 5. Custom Documentation Solution (Rejected)
**Rejected**: Building custom documentation would require significant development effort and wouldn't provide the ecosystem benefits of OpenAPI standards.

## Consequences

### Positive
- **Developer Experience**: Interactive documentation significantly improves API usability and adoption
- **Frontend Development**: Comprehensive API documentation accelerates frontend team development
- **Third-Party Integration**: Clear documentation enables partner and customer integrations
- **Maintenance Efficiency**: Auto-generated documentation stays synchronized with code changes
- **API Standards Compliance**: OpenAPI 3.0 specification ensures industry-standard documentation
- **Multiple Interfaces**: Swagger UI and ReDoc serve different use cases and preferences
- **Comprehensive Coverage**: All 50+ endpoints documented with examples and error handling
- **Security Clarity**: Tenant isolation and authentication clearly explained

### Negative
- **Initial Setup Overhead**: Comprehensive documentation requires initial time investment for setup and annotation
- **Schema Generation Warnings**: Some serializer fields generate warnings that need periodic review
- **Documentation Maintenance**: Keeping examples and descriptions current requires ongoing attention
- **Performance Impact**: Schema generation adds minimal but measurable request overhead

### Neutral
- **Learning Curve**: Team members need to learn drf-spectacular annotation patterns
- **Code Verbosity**: Documentation decorators increase code length but improve clarity
- **Dependency Addition**: New dependency on drf-spectacular adds to project complexity

## Validation Results

### Functional Validation
- ✅ **Schema Generation**: OpenAPI 3.0.3 schema generates successfully with comprehensive coverage
- ✅ **Interactive Documentation**: Swagger UI provides fully functional API testing interface
- ✅ **Alternative Interface**: ReDoc provides comprehensive documentation viewing experience
- ✅ **Authentication Integration**: Session authentication properly integrated with documentation
- ✅ **Example Accuracy**: All response examples reflect actual API behavior
- ✅ **Error Documentation**: Error responses properly documented with appropriate HTTP status codes

### Coverage Validation
- ✅ **Endpoint Coverage**: All major ViewSets (15+) comprehensively documented
- ✅ **Operation Coverage**: CRUD operations, custom actions, and bulk operations documented
- ✅ **Parameter Coverage**: Query parameters, path parameters, and request bodies specified
- ✅ **Response Coverage**: Success responses, error responses, and status codes documented
- ✅ **Security Coverage**: Authentication requirements and tenant isolation explained

### Quality Validation
- ✅ **Professional Presentation**: Documentation meets enterprise-grade standards
- ✅ **Comprehensive Examples**: Real-world usage patterns provided for complex operations
- ✅ **Clear Organization**: Logical grouping by functional areas with intuitive navigation
- ✅ **Accurate Information**: Documentation reflects actual API implementation
- ✅ **Developer-Friendly**: Interactive testing and comprehensive examples support development

### Performance Validation
- ✅ **Schema Generation Speed**: Documentation generates efficiently from existing codebase
- ✅ **Runtime Performance**: Minimal impact on API response times
- ✅ **Documentation Loading**: UI interfaces load quickly with proper asset optimization
- ✅ **Scalability**: Documentation architecture supports future endpoint additions

## Testing Strategy

### Documentation Accuracy Testing
```python
# Schema generation validation
python manage.py spectacular --color --file schema.yml

# Documentation endpoint testing
GET /api/schema/     # OpenAPI schema access
GET /api/docs/       # Swagger UI loading
GET /api/redoc/      # ReDoc interface loading
```

### Validation Scenarios
- **Schema Generation**: Verify complete OpenAPI schema generation without errors
- **Interactive Testing**: Validate Swagger UI functionality for key endpoints
- **Example Accuracy**: Ensure response examples match actual API behavior
- **Error Documentation**: Verify error response documentation accuracy
- **Authentication Flow**: Test documentation authentication integration

## Migration Strategy

### Phase 1: Core Documentation Infrastructure (Completed)
1. drf-spectacular installation and configuration
2. Basic SPECTACULAR_SETTINGS with API metadata
3. Documentation URL endpoint configuration
4. Schema generation validation

### Phase 2: Comprehensive Endpoint Documentation (Completed)
1. Major ViewSet documentation with @extend_schema_view decorators
2. Custom action documentation with detailed parameters
3. Response example creation with realistic data
4. Error response documentation and status codes

### Phase 3: Documentation Enhancement (Completed)
1. Interactive examples for complex operations
2. Workflow documentation for multi-step processes
3. Security and tenant isolation explanation
4. Professional description and API metadata

### Phase 4: Production Deployment (Ready)
1. Documentation asset optimization for production
2. Schema caching configuration for performance
3. Access control verification for documentation endpoints
4. Monitoring setup for documentation usage analytics

## Future Enhancements

### Planned Improvements
1. **Advanced Examples**: Dynamic example generation based on current data
2. **Workflow Diagrams**: Visual documentation for complex multi-step processes
3. **SDK Generation**: Auto-generated client libraries from OpenAPI schema
4. **API Versioning**: Documentation support for multiple API versions
5. **Custom Annotations**: Domain-specific documentation annotations for GRC terminology

### Long-term Considerations
1. **Internationalization**: Multi-language documentation support
2. **Interactive Tutorials**: Guided walkthroughs for common use cases
3. **Change Tracking**: Documentation changelog generation from schema diffs
4. **Usage Analytics**: Documentation endpoint usage tracking and optimization
5. **Community Contributions**: External developer documentation contributions

## References
- ADR-0013: Automated Assessment Reminder System
- ADR-0012: Assessment Reporting Architecture
- ADR-0011: Evidence Management Architecture
- ADR-0009: Control Assessment Architecture
- ADR-0002: User-Tenant Relationship via Schema Isolation
- Story 1.1: Framework & Control Catalog Implementation
- Story 1.2: Control Assessments Implementation
- Story 1.3: Evidence Management Implementation
- Story 1.4: Assessment Reporting Implementation
- Story 1.5: Automated Reminders Implementation

## Resolution Summary

This ADR documents the successful implementation of comprehensive API documentation using drf-spectacular and OpenAPI 3.0. The solution provides interactive documentation interfaces, comprehensive endpoint coverage, and maintains synchronization with code changes through automatic generation.

The documentation significantly enhances developer experience, supports frontend development, and enables third-party integrations while maintaining enterprise-grade quality and security standards. The implementation is production-ready and provides the foundation for future API evolution and community adoption.

**Implementation Status: ✅ Complete and Production Ready**