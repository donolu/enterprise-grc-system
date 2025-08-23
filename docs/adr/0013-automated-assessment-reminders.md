# ADR-0013: Automated Assessment Reminder System

## Status
Accepted

## Context
Following the successful implementation of Stories 1.1-1.4 (Framework & Control Catalog, Control Assessments, Evidence Management, and Assessment Reporting), the system needed automated reminder capabilities to ensure timely completion of assessments and maintain compliance momentum. The reminder system required support for configurable user preferences, multiple notification types, professional email templates, and scalable delivery infrastructure while maintaining security and tenant isolation.

### Problem Statement
Organizations conducting compliance assessments need:
- Automated reminders for upcoming and overdue assessment deadlines
- Configurable notification preferences per user with flexible timing options
- Professional email templates with urgency-appropriate styling and messaging
- Weekly digest summaries of assessment workload and priorities  
- Duplicate prevention to avoid notification fatigue
- Administrative tools for bulk reminder management and troubleshooting
- Scalable infrastructure supporting high-volume reminder processing
- Integration with existing assessment workflow and evidence management systems

### Existing Infrastructure Analysis
- ✅ **Email Infrastructure**: SMTP configuration with Django mail backend already established
- ✅ **Celery Infrastructure**: Async task processing and Celery Beat scheduling configured
- ✅ **Assessment Models**: Rich ControlAssessment model with due dates, status tracking, and user assignments
- ✅ **Multi-tenant Architecture**: Established tenant isolation patterns and user scoping
- ✅ **Notification Patterns**: Billing notification service providing proven email template patterns
- ✅ **Admin Interface**: Django admin with advanced bulk operations and management capabilities

## Decision
We implemented a comprehensive automated reminder system that provides configurable per-user notification preferences, smart reminder logic with duplicate prevention, professional email templates, and robust administrative management while maintaining consistency with established architectural patterns and security controls.

### Key Architecture Decisions

#### 1. Per-User Configuration Model
```python
class AssessmentReminderConfiguration(models.Model):
    user = models.OneToOneField(User, related_name='reminder_config')
    enable_reminders = models.BooleanField(default=True)
    advance_warning_days = models.PositiveIntegerField(default=7)
    reminder_frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)
    custom_reminder_days = models.JSONField(default=list)
    weekly_digest_enabled = models.BooleanField(default=True)
```

**Rationale**: Individual user control over notification preferences prevents notification fatigue while accommodating different work styles and organizational cultures.

#### 2. Duplicate Prevention Architecture
```python
class AssessmentReminderLog(models.Model):
    assessment = models.ForeignKey(ControlAssessment)
    user = models.ForeignKey(User)
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPES)
    days_before_due = models.IntegerField()
    sent_at = models.DateTimeField(auto_now_add=True)
    email_sent = models.BooleanField(default=False)
    
    class Meta:
        unique_together = [('assessment', 'user', 'reminder_type', 'days_before_due')]
```

**Rationale**: Comprehensive logging with unique constraints prevents duplicate reminders while providing audit trail and troubleshooting capabilities.

#### 3. Service-Oriented Reminder Architecture
```python
class AssessmentReminderService:
    @staticmethod
    def send_individual_reminder(assessment, user, reminder_type, days_before_due):
        # Smart reminder logic with configuration checks and duplicate prevention
        
    @staticmethod
    def process_daily_reminders():
        # Main processing function for all daily reminders
```

**Rationale**: Service abstraction allows for easy testing, configuration management, and future enhancement while maintaining separation of concerns.

#### 4. Multi-Template Email System
```
templates/catalogs/emails/
├── assessment_reminder.html/txt     # Individual reminders with urgency styling
├── weekly_digest.html/txt          # Comprehensive weekly summaries
├── assignment_notification.html/txt # Immediate assignment alerts
└── status_change_notification.html/txt # Status update notifications
```

**Rationale**: Specialized templates for different notification types provide appropriate urgency indicators and relevant information for each use case.

#### 5. Celery Task Infrastructure
```python
@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def send_due_reminders(self):
    # Daily processing with retry logic and error handling

CELERY_BEAT_SCHEDULE = {
    "assessments_due_reminders_daily": {
        "task": "catalogs.tasks.send_due_reminders",
        "schedule": crontab(hour=8, minute=0),  # 8 AM daily
    }
}
```

**Rationale**: Reliable scheduled processing with error handling and retry logic ensures consistent reminder delivery even during system issues.

### Reminder Logic Specifications

#### Reminder Types and Triggers
1. **Advance Warning Reminders**: Sent N days before due date (user configurable, default 7)
2. **Due Today Reminders**: Sent on the assessment due date with high priority styling
3. **Overdue Reminders**: Sent for past-due assessments with escalating urgency
4. **Weekly Digests**: Comprehensive summary sent on user-configured day of week
5. **Assignment Notifications**: Immediate alerts when assessments are assigned
6. **Status Change Notifications**: Updates for significant status transitions

#### Smart Configuration Logic
```python
def get_reminder_days(self):
    if self.reminder_frequency == 'custom' and self.custom_reminder_days:
        return sorted(self.custom_reminder_days, reverse=True)
    elif self.reminder_frequency == 'weekly':
        return [7, 14, 21]  # Weekly reminders
    else:  # daily
        return list(range(1, self.advance_warning_days + 1))
```

#### Urgency Classification System
- **Critical**: Overdue > 7 days (red styling, urgent language)
- **High**: Due today or overdue ≤ 7 days (orange styling, immediate action)
- **Medium**: Due within 3 days (yellow styling, preparation needed)
- **Low**: Due > 3 days (green styling, awareness level)

### Email Template Architecture

#### Professional Visual Design
- Responsive HTML templates with mobile optimization
- Color-coded urgency indicators with consistent branding
- Professional typography with clear hierarchy and calls-to-action
- Framework badges and assessment metadata display
- Action buttons linking to assessment management interface

#### Content Personalization
- User-specific greeting and assessment assignment context
- Configurable content sections (assessment details, remediation items)
- Framework-specific information and compliance context
- Next steps guidance based on assessment status and urgency
- Notification preference management links

### Administrative Management

#### Enhanced Admin Interface
```python
@admin.register(AssessmentReminderConfiguration)
class AssessmentReminderConfigurationAdmin(admin.ModelAdmin):
    actions = [
        'enable_reminders_bulk',
        'disable_reminders_bulk', 
        'test_reminder_configuration',
        'send_immediate_digest'
    ]
```

#### Bulk Operations Support
- Mass enable/disable reminders for user groups
- Test reminder functionality for configuration validation
- Immediate digest sending for administrative override
- Bulk assessment reminder triggering from assessment admin
- Comprehensive logging review and status monitoring

## Implementation Details

### Database Schema Design
```sql
-- Reminder configuration with flexible timing options
CREATE TABLE catalogs_assessmentreminderconfig (
    user_id INTEGER UNIQUE REFERENCES auth_user(id),
    enable_reminders BOOLEAN DEFAULT TRUE,
    advance_warning_days INTEGER DEFAULT 7,
    reminder_frequency VARCHAR(10) DEFAULT 'daily',
    custom_reminder_days JSON DEFAULT '[]',
    weekly_digest_enabled BOOLEAN DEFAULT TRUE,
    digest_day_of_week INTEGER DEFAULT 1  -- Monday
);

-- Comprehensive reminder audit log
CREATE TABLE catalogs_assessmentreminderlog (
    assessment_id INTEGER REFERENCES catalogs_controlassessment(id),
    user_id INTEGER REFERENCES auth_user(id),
    reminder_type VARCHAR(20) NOT NULL,
    days_before_due INTEGER,
    sent_at TIMESTAMP DEFAULT NOW(),
    email_sent BOOLEAN DEFAULT FALSE,
    UNIQUE(assessment_id, user_id, reminder_type, days_before_due)
);
```

### Performance Optimization
- Efficient database queries with select_related and prefetch_related
- Batch processing of reminders to minimize database connections
- Strategic indexing on common query patterns (user, due_date, status)
- Cleanup tasks for reminder log maintenance and storage optimization

### Security Implementation
- Tenant isolation maintained through existing user scoping patterns
- Email content sanitization and template security validation
- User permission checking for administrative bulk operations
- Secure email transmission with proper authentication and encryption

### Error Handling and Resilience
- Comprehensive exception handling with graceful degradation
- Retry logic for transient failures (network, SMTP issues)
- Detailed logging for troubleshooting and monitoring
- Fallback mechanisms for critical reminder delivery

## Alternatives Considered

### 1. Third-Party Notification Service
**Rejected**: Would introduce external dependencies, cost considerations, and potential data privacy concerns while breaking tenant data locality principles.

### 2. Real-Time Push Notifications
**Rejected**: Email remains the most reliable and universally accessible notification method for compliance workflows. Push notifications could be added as enhancement.

### 3. Single Notification Template
**Rejected**: Different reminder types require different urgency levels and content depth to be effective for user decision-making.

### 4. Immediate Email Sending
**Rejected**: Async processing prevents UI blocking and provides better scalability and error handling for high-volume reminder processing.

### 5. Global Reminder Configuration
**Rejected**: Per-user configuration provides necessary flexibility for different work styles and organizational cultures while reducing notification fatigue.

## Consequences

### Positive
- **Automated Compliance Momentum**: Consistent reminder delivery maintains assessment progress and deadline awareness
- **Configurable User Experience**: Flexible notification preferences accommodate different work styles and reduce notification fatigue
- **Professional Communication**: High-quality email templates enhance organizational credibility and user engagement
- **Administrative Control**: Comprehensive management tools enable troubleshooting and bulk operations for compliance managers
- **Scalable Architecture**: Async processing and efficient database design support high-volume reminder processing
- **Audit Trail**: Complete logging provides compliance documentation and system troubleshooting capabilities
- **Integration Excellence**: Seamless integration with existing assessment and evidence management workflows
- **Future-Ready Design**: Extensible architecture supports tenant customization and additional notification types

### Negative
- **Email Dependency**: System effectiveness relies on reliable email infrastructure and user email engagement
- **Storage Growth**: Reminder logs accumulate over time, requiring periodic cleanup for storage optimization
- **Configuration Complexity**: Extensive customization options may overwhelm some users, though defaults address this
- **Processing Overhead**: Daily reminder processing requires system resources, mitigated by efficient async design

### Neutral
- **Email Deliverability**: Inherits existing email infrastructure capabilities and limitations
- **User Adoption**: Effectiveness depends on user engagement with email notifications and preference configuration
- **Tenant Scope**: Current design uses existing tenant isolation patterns without additional complexity

## Validation Results

### Functional Validation
- ✅ **Reminder Delivery**: All reminder types deliver successfully with proper content and timing
- ✅ **Duplicate Prevention**: Robust logging prevents redundant notifications while maintaining audit trail
- ✅ **Configuration Flexibility**: User preferences properly control notification behavior and timing
- ✅ **Admin Operations**: Bulk management functions work reliably with appropriate error handling
- ✅ **Template Quality**: Professional email rendering across different clients and devices

### Performance Validation
- ✅ **Processing Efficiency**: Daily reminder task completes efficiently for large user bases
- ✅ **Database Performance**: Optimized queries prevent N+1 problems and minimize processing time
- ✅ **Email Delivery Speed**: Async processing prevents UI blocking and supports bulk operations
- ✅ **Storage Efficiency**: Cleanup tasks maintain reasonable database size growth

### Security Validation
- ✅ **Tenant Isolation**: Reminders properly scoped to user's tenant with no cross-tenant leakage
- ✅ **User Authentication**: Proper permission checking for administrative operations
- ✅ **Email Security**: Template content properly sanitized and secure transmission maintained
- ✅ **Data Protection**: User preferences and reminder logs properly protected

### Integration Validation
- ✅ **Assessment Workflow**: Reminders properly integrate with existing assessment status and timeline management
- ✅ **Evidence Integration**: Evidence information correctly included in relevant reminder templates
- ✅ **Admin Interface**: Reminder management seamlessly integrated with existing assessment administration
- ✅ **Multi-tenant Compatibility**: System works correctly across different tenant configurations

## Testing Strategy

### Comprehensive Test Coverage
```python
class AssessmentReminderServiceTest(APITestCase):
    def test_send_individual_reminder(self):
    def test_weekly_digest_generation(self):
    def test_duplicate_prevention(self):
    def test_urgency_classification(self):
    
class ReminderIntegrationTest(TestCase):
    def test_end_to_end_reminder_workflow(self):
    def test_overdue_reminder_escalation(self):
```

### Validation Scenarios
- **Configuration Management**: User preference creation, modification, and application
- **Reminder Logic**: Timing calculation, duplicate prevention, and urgency classification
- **Template Rendering**: Email content generation and formatting validation
- **Error Handling**: Network failures, invalid data, and system recovery
- **Admin Operations**: Bulk actions, testing functionality, and monitoring capabilities

## Migration Strategy

### Phase 1: Core Infrastructure (Completed)
1. Database models for configuration and logging
2. Basic reminder service with individual notification capability
3. Core email templates for primary reminder types
4. Celery task integration with daily processing

### Phase 2: Advanced Features (Completed)
1. Weekly digest functionality with comprehensive summaries
2. Administrative interface with bulk operations and monitoring
3. Enhanced templates with urgency styling and rich content
4. Comprehensive test suite and validation framework

### Phase 3: Production Deployment (Ready)
1. Database migrations for tenant environments
2. Celery Beat configuration for scheduled processing
3. Email infrastructure validation and deliverability testing
4. Monitoring and alerting for reminder system health

## Future Enhancements

### Planned Improvements
1. **Tenant Customization**: Custom email templates and branding per tenant organization
2. **Mobile Push Notifications**: Supplement email with mobile app notifications for immediate alerts
3. **Reminder Analytics**: Usage statistics, engagement metrics, and effectiveness reporting
4. **Smart Scheduling**: Machine learning for optimal reminder timing based on user response patterns
5. **Integration APIs**: Third-party calendar and task management system integration

### Long-term Considerations
1. **Multi-Channel Notifications**: SMS, Slack, Microsoft Teams integration for diverse communication preferences
2. **Intelligent Content**: AI-powered reminder content optimization based on assessment context
3. **Workflow Automation**: Automatic assignment and escalation based on reminder non-response
4. **Compliance Reporting**: Reminder delivery documentation for audit and compliance requirements

## References
- ADR-0012: Assessment Reporting Architecture
- ADR-0011: Evidence Management Architecture  
- ADR-0009: Control Assessment Architecture
- ADR-0002: User-Tenant Relationship via Schema Isolation
- Story 1.1: Framework & Control Catalog Implementation
- Story 1.2: Control Assessments Implementation
- Story 1.3: Evidence Management Implementation
- Story 1.4: Assessment Reporting Implementation

## Resolution Summary

This ADR documents the successful implementation of comprehensive automated assessment reminder capabilities. The architecture provides configurable per-user notification preferences, smart reminder logic with duplicate prevention, professional email templates with urgency-appropriate styling, and robust administrative management while maintaining security and scalability.

The solution significantly enhances compliance workflow efficiency by ensuring timely assessment completion through automated notification delivery. The implementation is production-ready and provides the foundation for future tenant customization and advanced notification features.

**Implementation Status: ✅ Complete and Production Ready**