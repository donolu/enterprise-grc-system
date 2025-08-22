# ADR-0006: Configurable Subscription Limits with Dual Approval Workflow

## Status
Accepted

## Context
Following the implementation of the Stripe subscription billing system (ADR-0005), a critical need emerged for **flexible subscription limit management** beyond the static plan-based limits. The system required:

- **Runtime configurable limits** for individual tenants without code deployments
- **Governance controls** to prevent abuse and ensure business justification
- **Audit compliance** with full traceability of limit changes
- **Multi-stakeholder approval** to distribute responsibility and prevent single points of failure
- **Temporary override support** for short-term business needs
- **Integration with existing plan enforcement** to maintain seamless user experience

The static plan limits (Free: 3 users, Basic: 10 users, Enterprise: 100 users) were insufficient for:
- Enterprise customers with unique requirements
- Seasonal business fluctuations requiring temporary increases
- Pilot programs and proof-of-concept deployments
- Emergency situations requiring immediate limit increases

## Decision
We have implemented a comprehensive **Database-Driven Configurable Limits System** with **Dual Approval Workflow** that provides maximum flexibility while maintaining strict governance controls.

### 1. Enhanced Data Model Architecture
**Custom Limit Overrides in Subscription Model**:
```python
class Subscription(models.Model):
    # ... existing fields ...
    
    # Custom limit overrides (null = use plan default)
    custom_max_users = models.PositiveIntegerField(null=True, blank=True)
    custom_max_documents = models.PositiveIntegerField(null=True, blank=True) 
    custom_max_frameworks = models.PositiveIntegerField(null=True, blank=True)
    custom_max_storage_gb = models.PositiveIntegerField(null=True, blank=True)
    
    def get_effective_user_limit(self):
        return self.custom_max_users or self.plan.max_users
```

**Approval Workflow Model**:
```python
class LimitOverrideRequest(models.Model):
    # Request details
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    limit_type = models.CharField(max_length=20, choices=LIMIT_TYPES)
    current_limit = models.PositiveIntegerField()
    requested_limit = models.PositiveIntegerField()
    
    # Business context
    business_justification = models.TextField()
    urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES)
    temporary = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Dual approval tracking
    first_approver = models.CharField(max_length=255, blank=True)
    first_approved_at = models.DateTimeField(null=True, blank=True)
    second_approver = models.CharField(max_length=255, blank=True)  
    second_approved_at = models.DateTimeField(null=True, blank=True)
```

### 2. Dual Approval Workflow Design
**Two-Step Approval Process**:
1. **First Approval**: Initial review and approval by authorized personnel
2. **Second Approval**: Independent verification by different approver
3. **Administrative Application**: Final step requiring admin privileges to activate

**Approval Safeguards**:
- Same person cannot provide both approvals
- Business justification required for all requests
- Urgency levels determine review timeframes
- Full audit trail with timestamps and notes
- Automated email notifications at each stage

**Workflow States**:
```
pending → first_approval → second_approval → approved → applied
    ↓
rejected (at any stage)
```

### 3. Comprehensive Request Management System
**Request Types and Parameters**:
- **Limit Types**: Users, Documents, Frameworks, Storage (GB)
- **Urgency Levels**: Low (standard), Medium (24hr), High (same day), Critical (immediate)
- **Override Duration**: Permanent or Temporary with expiration dates
- **Business Context**: Mandatory justification with minimum 20 characters

**Request Validation**:
- Positive limit values only
- Meaningful business justification required
- Expiration date mandatory for temporary overrides
- Current limit calculation based on effective limits

### 4. RESTful API Design
**Complete CRUD Operations**:
```
POST   /api/limit-overrides/                 # Submit new request
GET    /api/limit-overrides/                 # List tenant requests
GET    /api/limit-overrides/{id}/            # View specific request
POST   /api/limit-overrides/{id}/approve_first/   # First approval
POST   /api/limit-overrides/{id}/approve_second/  # Second approval
POST   /api/limit-overrides/{id}/reject/          # Reject request
POST   /api/limit-overrides/{id}/apply_override/  # Apply approved override
GET    /api/limit-overrides/pending_approvals/    # Approver dashboard
```

**Permission-Based Access Control**:
- **Tenant Users**: View own requests, submit new requests
- **Approvers**: View and approve pending requests across all tenants
- **Administrators**: Full access including application of approved overrides

### 5. Integration with Plan Enforcement
**Seamless Effective Limits**:
```python
def get_effective_user_limit(self):
    return self.custom_max_users if self.custom_max_users is not None else self.plan.max_users
```

**Enhanced Usage Tracking**:
- Real-time usage validation uses effective limits
- Override status included in usage summaries
- Upgrade recommendations consider custom overrides
- Plan enforcement decorators automatically use effective limits

**Backward Compatibility**:
- Existing plan enforcement continues to work unchanged
- API responses include override status for transparency
- No breaking changes to current limit checking logic

### 6. Notification and Communication System
**Multi-Stage Email Notifications**:
- **New Request**: Notify all approvers of pending request
- **First Approval**: Alert about need for second approval
- **Final Approval**: Notify admins that override can be applied
- **Application**: Confirm override is now active
- **Rejection**: Inform relevant parties with reasoning

**Configurable Notification Recipients**:
```python
# Environment-based configuration
LIMIT_OVERRIDE_APPROVER_EMAILS = ["approver1@company.com", "approver2@company.com"]
ADMIN_NOTIFICATION_EMAILS = ["admin@company.com"]
```

**Rich Context in Notifications**:
- Tenant information and current plan
- Limit type and requested changes
- Business justification and urgency level
- Approval history and next required actions
- Direct links to approval interface

## Alternatives Considered

### Static Environment Configuration
- **Pros**: Simple implementation, version controlled
- **Cons**: Requires deployment for changes, not tenant-specific
- **Rejected**: Insufficient flexibility for multi-tenant SaaS needs

### Single Approval Workflow  
- **Pros**: Faster approval process, less complexity
- **Cons**: Single point of failure, higher abuse risk
- **Rejected**: Insufficient governance for financial impacts

### External Approval Systems
- **Pros**: Integration with existing enterprise workflows
- **Cons**: Additional complexity, vendor dependencies
- **Rejected**: Over-engineering for current requirements

### Admin-Only Limit Changes
- **Pros**: Maximum control, simple implementation
- **Cons**: Creates bottlenecks, no self-service capability
- **Rejected**: Poor scalability and user experience

## Consequences

### Positive
- **Maximum Flexibility**: Runtime limit adjustments without deployments
- **Strong Governance**: Dual approval prevents abuse and ensures accountability
- **Comprehensive Audit**: Complete traceability for compliance and debugging
- **Self-Service Capability**: Tenants can request overrides independently
- **Emergency Support**: Critical urgency level for immediate needs
- **Temporary Overrides**: Support for short-term business requirements
- **Seamless Integration**: Works transparently with existing plan enforcement

### Negative
- **Increased Complexity**: More models, API endpoints, and business logic
- **Approval Overhead**: Two-step process may delay urgent legitimate requests
- **Administrative Burden**: Requires ongoing management of approver lists
- **Email Dependencies**: Notification failures could impact approval workflow

### Risks and Mitigations
- **Approval Bottlenecks**: Mitigated by urgency levels and multiple approvers
- **Configuration Drift**: Mitigated by audit trails and admin oversight
- **Notification Failures**: Mitigated by fallback to admin interface access
- **Data Integrity**: Mitigated by database constraints and validation

## Implementation Details

### Database Schema
```sql
-- Custom limits in subscriptions
ALTER TABLE subscriptions ADD custom_max_users INTEGER NULL;
ALTER TABLE subscriptions ADD custom_max_documents INTEGER NULL;
ALTER TABLE subscriptions ADD custom_max_frameworks INTEGER NULL;
ALTER TABLE subscriptions ADD custom_max_storage_gb INTEGER NULL;

-- Override request tracking
CREATE TABLE limit_override_requests (
    id SERIAL PRIMARY KEY,
    subscription_id INTEGER NOT NULL,
    limit_type VARCHAR(20) NOT NULL,
    current_limit INTEGER NOT NULL,
    requested_limit INTEGER NOT NULL,
    business_justification TEXT NOT NULL,
    urgency VARCHAR(10) DEFAULT 'low',
    -- ... approval tracking fields
);
```

### API Usage Examples
```bash
# Submit override request
curl -X POST /api/limit-overrides/ \
  -H "Content-Type: application/json" \
  -d '{
    "limit_type": "max_users",
    "requested_limit": 50,
    "business_justification": "Expanding development team for Q4 project",
    "urgency": "medium"
  }'

# Provide first approval
curl -X POST /api/limit-overrides/123/approve_first/ \
  -d '{"notes": "Approved for legitimate business expansion"}'

# Apply approved override
curl -X POST /api/limit-overrides/123/apply_override/
```

### Environment Configuration
```bash
# .env configuration
LIMIT_OVERRIDE_APPROVER_EMAILS=manager@company.com,director@company.com
ADMIN_NOTIFICATION_EMAILS=admin@company.com,devops@company.com
```

## Success Metrics
- ✅ Database-driven limit configuration with runtime flexibility
- ✅ Dual approval workflow with different-person requirement
- ✅ Four configurable limit types (users, documents, frameworks, storage)
- ✅ Comprehensive API with 8+ endpoints for full request lifecycle
- ✅ Email notification system with 5 distinct notification types
- ✅ Seamless integration with existing plan enforcement system
- ✅ Business justification and urgency level requirements
- ✅ Temporary override support with expiration handling
- ✅ Full audit trail with timestamps and approver tracking
- ✅ Permission-based access control for different user roles

## Future Considerations
- Implement automatic expiration cleanup for temporary overrides
- Add integration with external approval systems (JIRA, ServiceNow)
- Create mobile-friendly approval interface for urgent requests
- Implement usage-based auto-scaling with approval thresholds
- Add statistical analysis of override patterns for plan optimization
- Consider integration with financial systems for cost impact analysis
- Implement approval delegation for vacation/unavailability scenarios

## References
- Story 0.5: Setup Subscription & Billing (Stripe)
- ADR-0005: Stripe Subscription Billing System  
- Django Multi-Tenant Architecture Documentation
- Database Design Patterns for Approval Workflows