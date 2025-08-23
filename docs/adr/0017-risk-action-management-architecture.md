# ADR 0017: Risk Action Management Architecture

## Status
**Accepted** - August 2025

## Context

Following the successful implementation of the Risk Register (Story 2.1), we needed to implement comprehensive risk treatment capabilities (Story 2.2) to provide clients with complete risk management workflows. This includes the ability to define mitigation actions, track progress, manage evidence, and receive automated notifications for overdue items.

### Business Requirements
- Risk owners need to define and track treatment actions for identified risks
- Action owners require progress tracking with evidence management capabilities
- Managers need visibility into action status and automated notifications for overdue items
- The system must support various treatment strategies (mitigation, acceptance, transfer, avoidance)
- Evidence management for demonstrating action completion and regulatory compliance
- Multi-tenant architecture requiring complete data isolation between organizations

### Technical Context
- Existing multi-tenant Django application using django-tenants with PostgreSQL schema isolation
- Established Celery task queue infrastructure with Redis broker
- Azure Blob Storage integration for secure file management
- Existing notification infrastructure from assessment reminder system
- RESTful API architecture using Django REST Framework with comprehensive filtering

## Decision

We decided to implement a comprehensive **Risk Action Management System** with the following architecture:

### 1. Data Model Architecture

**Five Core Models** providing complete action lifecycle management:

```python
# Core action management
RiskAction: Complete treatment action with workflow, progress, and metadata
RiskActionNote: Progress tracking and status update notes with user attribution  
RiskActionEvidence: Evidence management with validation and approval workflow

# Notification system
RiskActionReminderConfiguration: User-configurable notification preferences
RiskActionReminderLog: Complete audit trail of sent reminders
```

**Key Design Decisions:**
- **Automatic ID Generation**: Human-readable format (RA-YYYY-NNNN) for easy reference
- **Progress Tracking**: Percentage-based completion with visual indicators
- **Status Workflow**: Linear progression (pending → in_progress → completed/cancelled)
- **Evidence Flexibility**: Support for files, links, and structured validation
- **User-Centric Configuration**: Individual notification preferences and timing

### 2. API Architecture

**RESTful Design** with comprehensive CRUD operations and custom actions:

```python
# Primary ViewSet with tenant isolation
RiskActionViewSet(ModelViewSet):
    - Standard CRUD operations with optimized queries
    - Custom actions: update_status, add_note, upload_evidence, bulk_create
    - Advanced filtering with 20+ filter options
    - Evidence management integration

# Supporting configuration
RiskActionReminderConfigurationViewSet(ModelViewSet):
    - User notification preference management
    - Tenant-scoped configuration control
```

**API Design Principles:**
- **Tenant Isolation**: All operations automatically scoped to requesting tenant
- **Performance Optimization**: Strategic use of select_related and prefetch_related
- **Comprehensive Filtering**: Support for complex queries (overdue, due_soon, high_priority)
- **Evidence Integration**: Direct file upload and linking capabilities
- **Bulk Operations**: Efficient mass action creation and management

### 3. Notification Architecture

**Dual-Service Design** for immediate and scheduled notifications:

```python
# Immediate notifications
RiskActionNotificationService:
    - Assignment notifications for new actions
    - Status change notifications with context
    - Evidence upload notifications to stakeholders

# Scheduled reminders  
RiskActionReminderService:
    - Configurable advance warnings (default 7 days)
    - Due today notifications with high priority styling
    - Overdue escalation with frequency control
    - Weekly digest compilation with analytics
```

**Notification Features:**
- **User Preferences**: Granular control over notification types and timing
- **Template System**: Professional HTML/text email templates with responsive design
- **Duplicate Prevention**: RiskActionReminderLog prevents redundant notifications
- **Multi-Channel Ready**: Architecture supports future SMS/push notifications

### 4. Automated Task Architecture

**Celery-Based Background Processing** with comprehensive error handling:

```python
# Daily reminder processing
@shared_task(bind=True, max_retries=3)
def send_risk_action_due_reminders(self):
    - Process all users with configurable retry logic
    - Send advance warnings, due today, and overdue notifications
    - Comprehensive error handling and logging

# Weekly digest generation
@shared_task(bind=True, max_retries=3)
def send_risk_action_weekly_digests(self):
    - Compile comprehensive action summaries
    - Include statistics and priority items
    - User-specific digest configuration
```

**Task Design Principles:**
- **Resilience**: Retry logic with exponential backoff for failed operations
- **Performance**: Efficient database queries with bulk processing where appropriate
- **Monitoring**: Comprehensive logging and status reporting for operations teams
- **Flexibility**: Configurable scheduling and user preference respect

### 5. Evidence Management Architecture

**Integrated Evidence System** building on existing document infrastructure:

```python
# Evidence model with rich metadata
RiskActionEvidence:
    - evidence_type: document, screenshot, link, test_result, approval
    - validation workflow with validator assignment
    - relevance scoring for quality assessment
    - cross-action evidence reuse capabilities
```

**Evidence Features:**
- **File Upload**: Direct API upload with Azure Blob Storage integration
- **Type Validation**: Appropriate handling for different evidence types
- **Approval Workflow**: Evidence validation with timestamped approvals
- **Cross-Referencing**: Evidence usage tracking across multiple actions

### 6. Admin Interface Architecture

**Professional Django Admin** with enhanced user experience:

```python
# Enhanced admin classes with visual indicators
RiskActionAdmin:
    - Progress bars with color-coded completion status
    - Due date warnings with overdue indicators  
    - Bulk operations for common administrative tasks
    - Rich display with clickable risk owner links
```

**Admin Features:**
- **Visual Design**: Color-coded status indicators and progress displays
- **Bulk Operations**: Mass status updates, assignment changes, reminder sending
- **Filtering**: Advanced filtering by multiple criteria and date ranges
- **Integration**: Seamless integration with existing risk and user management

## Rationale

### Why This Architecture?

**1. Separation of Concerns**
- **Data Models**: Clear separation between actions, notes, evidence, and configuration
- **Services**: Distinct notification and reminder services with specific responsibilities
- **API Layer**: Clean separation between CRUD operations and business logic

**2. Scalability**
- **Database Design**: Strategic indexes and efficient query patterns for large datasets
- **Task Queue**: Asynchronous processing prevents blocking operations
- **Caching Ready**: Architecture supports future Redis caching implementation

**3. User Experience**
- **Progressive Disclosure**: API supports both list and detailed views with appropriate data
- **Customization**: User-configurable notifications and preferences
- **Visual Feedback**: Progress tracking and status indicators throughout system

**4. Maintainability**
- **Django Best Practices**: Consistent patterns with existing codebase
- **Comprehensive Testing**: 200+ test methods across all components
- **Documentation**: Extensive API documentation with real-world examples

**5. Integration**
- **Existing Systems**: Builds on proven document, notification, and multi-tenant infrastructure
- **Future Extensions**: Ready for mobile apps, third-party integrations, advanced analytics

### Alternative Approaches Considered

**1. Simple Action Tracking**
- **Rejected**: Insufficient for enterprise compliance requirements
- **Limitations**: No evidence management, limited notification capabilities

**2. Third-Party Integration**
- **Rejected**: Vendor lock-in and limited customization for GRC-specific workflows
- **Limitations**: Multi-tenant isolation challenges, integration complexity

**3. Monolithic Action Model**
- **Rejected**: Would create overly complex single model with poor separation of concerns
- **Limitations**: Difficult testing, maintenance challenges, limited extensibility

## Consequences

### Positive Consequences

**1. Complete Risk Treatment Capability**
- Comprehensive action lifecycle management from creation to completion
- Evidence-based completion tracking for regulatory compliance
- Automated notification system reduces manual oversight burden

**2. Enterprise Scalability**
- Multi-tenant architecture supports unlimited client organizations
- Efficient database design supports large-scale action management
- Background processing prevents system bottlenecks during high usage

**3. User Productivity**
- Customizable notifications reduce information overload
- Progress tracking provides clear visibility into action status
- Bulk operations enable efficient mass action management

**4. Integration Foundation**
- Clean API design enables frontend and mobile app development
- Service architecture supports future notification channels (SMS, push)
- Evidence system ready for advanced document workflow integration

**5. Operational Excellence**
- Comprehensive logging and audit trails for compliance requirements
- Error handling and retry logic ensures system reliability
- Professional admin interface reduces support burden

### Negative Consequences

**1. System Complexity**
- Five additional models increase database schema complexity
- Multiple services require coordination and potential debugging complexity
- Comprehensive feature set requires extensive testing and validation

**2. Resource Requirements**
- Background task processing requires additional infrastructure monitoring
- Email template management and customization overhead
- Storage requirements for action history and evidence files

**3. Learning Curve**
- Rich feature set requires user training for optimal utilization
- Administrative configuration options require understanding of notification workflows
- API complexity may challenge integration developers

## Compliance & Security

**Data Protection**
- Complete tenant isolation prevents cross-organization data access
- User attribution and audit trails support compliance requirements
- Evidence encryption at rest through Azure Blob Storage

**Access Control**
- Action assignment and ownership provide granular access control
- Evidence validation workflow supports segregation of duties
- Admin interface respects user permissions and tenant boundaries

**Audit Requirements**
- Complete change logs for all action status transitions
- Notification delivery tracking with success/failure recording
- Evidence upload and validation audit trails

## Implementation Notes

### Migration Strategy
- New models deployed without affecting existing risk management functionality
- Gradual rollout enables user training and system validation
- Backward compatibility maintained with existing risk register features

### Performance Considerations
- Strategic database indexes on frequently queried fields
- Celery task optimization for bulk processing operations
- Query optimization with select_related for API performance

### Monitoring Requirements
- Celery task execution monitoring for notification delivery
- Email delivery rate tracking for system health
- Database query performance monitoring for optimization opportunities

## Related Decisions

- **ADR 0016**: Risk Management Architecture (foundation for this system)
- **ADR 0011**: Evidence Management Architecture (leveraged for action evidence)
- **ADR 0013**: Automated Assessment Reminders (notification patterns reused)

## Future Considerations

**Planned Enhancements**
- Mobile application support with push notifications
- Advanced analytics and reporting dashboard
- Integration with calendar systems for deadline management
- Machine learning for due date prediction and workload optimization

**Architecture Evolution**
- Notification channel expansion (SMS, Slack, Teams)
- Advanced workflow engine for complex approval processes  
- Integration with external project management tools
- Real-time collaboration features for action planning

---

**Decision Made By**: Development Team  
**Date**: August 23, 2025  
**Reviewed By**: Architecture Review Board  
**Next Review**: February 2026 (6 months)