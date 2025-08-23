# ADR-0009: Control Assessment Architecture

## Status
Accepted

## Context
Following the implementation of the Framework & Control Catalog (ADR-0008), we needed to implement a comprehensive control assessment system that allows organizations to evaluate their compliance posture against framework controls. The system needed to support multi-tenant isolation, workflow management, evidence linking, and progress tracking while maintaining the flexibility to handle various compliance frameworks (ISO 27001, SOC 2, NIST CSF, etc.).

## Decision
We implemented a comprehensive control assessment architecture centered around the `ControlAssessment` model with the following key components:

### Core Assessment Model
- **ControlAssessment**: Primary model linking tenants to controls with assessment data
- **AssessmentEvidence**: Junction model for linking evidence to assessments with relevance scoring
- Multi-step workflow management with status transitions
- Comprehensive audit logging and change tracking

### Key Design Decisions

#### 1. Assessment Workflow Design
```python
STATUS_CHOICES = [
    ('not_started', 'Not Started'),
    ('pending', 'Pending'),
    ('in_progress', 'In Progress'),
    ('under_review', 'Under Review'),
    ('complete', 'Complete'),
    ('not_applicable', 'Not Applicable'),
    ('deferred', 'Deferred'),
]
```

**Rationale**: Multi-step workflow provides clear progression tracking and supports enterprise compliance processes with review stages.

#### 2. Applicability Determination
```python
APPLICABILITY_CHOICES = [
    ('applicable', 'Applicable'),
    ('not_applicable', 'Not Applicable'),
    ('to_be_determined', 'To Be Determined'),
]
```

**Rationale**: Separates applicability assessment from implementation status, allowing organizations to properly scope their compliance efforts.

#### 3. Implementation Status Tracking
```python
IMPLEMENTATION_STATUS_CHOICES = [
    ('not_implemented', 'Not Implemented'),
    ('partially_implemented', 'Partially Implemented'),
    ('implemented', 'Implemented'),
    ('not_applicable', 'Not Applicable'),
]
```

**Rationale**: Provides granular tracking of control implementation progress separate from assessment workflow status.

#### 4. Evidence Linking Architecture
- Many-to-many relationship between assessments and control evidence
- Relevance scoring (0-100) for evidence quality assessment
- Primary evidence designation for key documentation
- Complete audit trail of evidence associations

**Rationale**: Flexible evidence model supports various compliance documentation patterns while maintaining traceability.

### API Design Patterns

#### RESTful Endpoint Structure
```
GET/POST /api/catalogs/assessments/
GET/PUT/PATCH/DELETE /api/catalogs/assessments/{id}/
POST /api/catalogs/assessments/{id}/update_status/
POST /api/catalogs/assessments/{id}/link_evidence/
POST /api/catalogs/assessments/bulk_create/
GET /api/catalogs/assessments/my_assignments/
GET /api/catalogs/assessments/progress_report/
```

**Rationale**: Follows REST conventions while providing specialized endpoints for common business operations.

#### Serializer Specialization
- **List Serializer**: Optimized for list views with summary data
- **Detail Serializer**: Complete assessment data with related information
- **Create/Update Serializer**: Validation and business logic for mutations
- **Bulk Operations Serializer**: Efficient mass operations
- **Progress Reporting Serializer**: Analytics and statistical data

**Rationale**: Specialized serializers optimize API performance and provide appropriate data granularity for different use cases.

### Multi-tenant Integration

#### Tenant Isolation Strategy
- Automatic tenant scoping via django-tenants schema isolation
- Tenant-specific assessment ID generation (`ASSESS-{timestamp}-{random}`)
- User permission integration with assessment ownership
- Cross-tenant data protection at the ORM level

**Rationale**: Leverages existing tenant isolation infrastructure while adding assessment-specific security measures.

### Performance Considerations

#### Database Optimization
- `select_related()` for foreign key relationships
- Efficient bulk operations for framework-wide assessments
- Indexed fields for common query patterns
- Optimized admin interface with controlled data loading

**Rationale**: Ensures system scalability as organizations assess large numbers of controls across multiple frameworks.

### Change Management & Audit Trail

#### Comprehensive Logging
```python
change_log = models.JSONField(
    default=list,
    help_text="JSON log of all changes made to this assessment"
)
```

- User attribution for all changes
- Timestamp tracking for workflow transitions
- Detailed change descriptions
- Complete audit trail for compliance purposes

**Rationale**: Provides compliance audit requirements and supports accountability in assessment processes.

## Alternatives Considered

### 1. Simple Boolean Assessment Model
**Rejected**: Too simplistic for enterprise compliance needs. Doesn't support workflow management or detailed implementation tracking.

### 2. Single Status Field Design
**Rejected**: Would conflate applicability, implementation status, and workflow status, reducing clarity and flexibility.

### 3. Embedded Evidence Storage
**Rejected**: Would create tight coupling and limit evidence reusability across multiple assessments.

### 4. Monolithic Assessment API
**Rejected**: Would create overly complex endpoints. Specialized endpoints provide better performance and usability.

## Consequences

### Positive
- **Comprehensive Workflow Support**: Full assessment lifecycle management from determination to completion
- **Evidence Traceability**: Clear links between assessments and supporting documentation
- **Progress Visibility**: Real-time progress tracking across frameworks and teams
- **Audit Compliance**: Complete change history for regulatory requirements
- **Scalability**: Efficient bulk operations for large-scale assessments
- **Multi-framework Support**: Flexible design supports various compliance frameworks
- **User Experience**: Specialized endpoints optimize frontend performance

### Negative
- **Model Complexity**: Rich feature set requires more complex database schema
- **API Surface Area**: Multiple specialized endpoints increase API complexity
- **Storage Requirements**: Comprehensive logging increases storage usage
- **Migration Complexity**: Schema changes require careful migration planning

### Migration Path
- Database migration required for new assessment models
- Existing framework and control data seamlessly integrates
- Admin interface extensions provide immediate usability
- API endpoints follow existing authentication and permission patterns

## Implementation Details

### Database Schema
- 2 new models: `ControlAssessment`, `AssessmentEvidence`
- 1 migration file with proper field constraints
- Foreign key relationships maintain referential integrity
- JSON fields for flexible metadata storage

### API Endpoints
- 8 specialized assessment endpoints
- 2 evidence management endpoints
- Comprehensive filtering, searching, and ordering
- Bulk operations support for efficiency

### Admin Interface
- Advanced filtering and search capabilities
- Visual indicators for overdue assessments
- Bulk actions for common operations
- Inline evidence management

### Testing Strategy
- Model validation and business logic tests
- API endpoint functionality and permission tests
- Serializer validation and transformation tests
- Integration tests with existing systems
- Admin interface functionality verification

## Future Considerations
- Integration with automated reminder system (Story 1.4)
- Evidence management enhancements (Story 1.3)
- Analytics dashboard development (Story 5.3)
- Workflow customization for different frameworks
- Integration with external assessment tools

## References
- ADR-0008: Framework & Control Catalog Architecture
- ADR-0002: User-Tenant Relationship via Schema Isolation
- Django-tenants documentation for multi-tenant patterns
- ISO 27001:2022 assessment requirements
- SOC 2 Type II control evaluation guidelines