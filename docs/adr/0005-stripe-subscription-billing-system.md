# ADR-0005: Stripe Subscription Billing System

## Status
Accepted

## Context
Story 0.5 required implementing a comprehensive subscription billing system for the multi-tenant GRC platform. The system needed:

- Multi-tier subscription plans (Free, Basic, Enterprise) with feature differentiation
- Secure payment processing with industry-standard compliance
- Plan enforcement to limit resource usage based on subscription tier
- Grandfathering support for existing customers during price changes
- Webhook processing for real-time billing event handling
- Customer self-service billing portal for invoice management
- Multi-tenant billing isolation to separate customer financials

## Decision
We have implemented Stripe as our primary billing provider with a comprehensive subscription management system featuring:

### 1. Stripe Integration Architecture
**Payment Processing**: Full Stripe integration using their hosted Checkout and Customer Portal:
- Stripe Checkout for subscription sign-ups and upgrades
- Stripe Customer Portal for self-service billing management
- Stripe API for programmatic subscription management
- Webhook endpoints for real-time event processing

**Security**: All payment data handled by Stripe's PCI-compliant infrastructure:
- No sensitive payment data stored locally
- Secure API key management via environment variables
- Webhook signature verification for data integrity

### 2. Data Model Design
**Plan Model**: Feature-based subscription tiers stored in public schema:
```python
class Plan(models.Model):
    name = models.CharField(max_length=50, unique=True)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    max_users = models.PositiveIntegerField()
    max_documents = models.PositiveIntegerField()
    has_api_access = models.BooleanField()
    # ... additional feature flags
```

**Subscription Model**: Tenant-specific billing state with Stripe synchronization:
```python
class Subscription(models.Model):
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    stripe_subscription_id = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    is_grandfathered = models.BooleanField(default=False)
    custom_price = models.DecimalField(null=True, blank=True)
```

**BillingEvent Model**: Comprehensive audit trail for all billing activities:
```python
class BillingEvent(models.Model):
    stripe_event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    data = models.JSONField(default=dict)
    processed = models.BooleanField(default=False)
```

### 3. Subscription Plan Structure
**Free Plan** ($0/month):
- 3 users maximum
- 50 documents storage limit  
- 1 compliance framework
- No API access or advanced features

**Basic Plan** ($49/month):
- 10 users maximum
- 500 documents storage limit
- 5 compliance frameworks
- API access enabled
- Standard support

**Enterprise Plan** ($199/month):
- 100 users maximum
- 10,000 documents storage limit
- Unlimited compliance frameworks
- Full API access
- Advanced reporting and analytics
- Priority support

### 4. Plan Enforcement System
**Decorator-Based Enforcement**: Fine-grained access control using Python decorators:
```python
@require_api_access
@check_document_limits
def upload_document(request):
    # Function implementation
```

**Real-Time Usage Tracking**: Live monitoring of resource consumption:
- Document count validation before upload
- User creation limits during registration
- Feature access checks for API endpoints

**Upgrade Prompts**: Intelligent upgrade recommendations based on usage patterns:
- Notifications when approaching limits (80% threshold)
- Contextual upgrade suggestions in UI
- Plan comparison data in API responses

### 5. Webhook Event Processing
**Comprehensive Event Handling**: Full lifecycle management via webhooks:
- `checkout.session.completed`: Process successful subscription purchases
- `customer.subscription.created/updated/deleted`: Sync subscription state
- `invoice.payment_succeeded/failed`: Update payment status
- Automatic retry logic for failed webhook processing

**Idempotency**: Prevent duplicate processing using Stripe event IDs:
```python
billing_event = BillingEvent.objects.create(
    stripe_event_id=event['id'],
    event_type=event['type'],
    data=event['data']
)
```

### 6. Grandfathering and Custom Pricing
**Legacy Plan Support**: Maintain existing customer pricing during plan changes:
- `custom_price` field overrides default plan pricing
- `is_grandfathered` flag identifies legacy customers
- Price change migration tools for bulk updates

**Flexible Pricing**: Support for custom enterprise deals and promotions.

## Alternatives Considered

### PayPal/Braintree
- **Pros**: Wide market acceptance, competitive transaction fees
- **Cons**: Less developer-friendly API, weaker subscription management
- **Rejected**: Stripe provides superior developer experience and feature set

### Paddle
- **Pros**: Merchant of record service, global tax compliance
- **Cons**: Higher fees, less flexibility for custom billing logic
- **Rejected**: Increased cost not justified for our target market

### Chargebee/Recurly
- **Pros**: Advanced subscription management features, dunning management
- **Cons**: Additional service complexity, higher monthly fees
- **Rejected**: Stripe's native features sufficient for initial requirements

### Build Custom Billing
- **Pros**: Complete control, no third-party dependencies
- **Cons**: PCI compliance burden, significant development time
- **Rejected**: Not core business value, regulatory complexity too high

## Consequences

### Positive
- **Rapid Implementation**: Stripe's mature API enabled fast development
- **Security Compliance**: PCI compliance handled by Stripe infrastructure
- **Customer Experience**: Professional billing portal and payment flow
- **Multi-Tenant Isolation**: Clean separation of billing data per tenant
- **Scalability**: Stripe handles payment volume scaling automatically
- **Feature Enforcement**: Robust plan limits prevent resource abuse
- **Revenue Optimization**: Easy A/B testing of pricing and plan features

### Negative
- **Vendor Lock-In**: Migration away from Stripe would require significant effort
- **Transaction Fees**: 2.9% + 30¢ per transaction impacts unit economics
- **Feature Limitations**: Some advanced billing scenarios may require workarounds
- **Webhook Reliability**: Dependent on webhook delivery for real-time updates

### Risks and Mitigations
- **Stripe Service Outages**: Mitigated by graceful degradation and billing event queuing
- **Webhook Processing Failures**: Mitigated by retry logic and manual reconciliation tools
- **Plan Limit Bypass**: Mitigated by enforcement at multiple application layers
- **Price Change Complexity**: Mitigated by grandfathering system and migration tools

## Implementation Details

### Configuration
```python
# Django settings
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
```

### API Endpoints
```
GET /api/plans/ - List available subscription plans
GET /api/billing/current_subscription/ - View tenant subscription
POST /api/billing/create_checkout_session/ - Start subscription flow
GET /api/billing/billing_portal/ - Access Stripe customer portal
POST /webhooks/stripe/ - Process Stripe webhook events
```

### Plan Enforcement Examples
```python
# Document upload with limits
@check_document_limits
def create_document(request):
    # Upload logic with automatic limit validation

# API access control
@require_api_access
def api_endpoint(request):
    # API logic restricted to paid plans
```

## Success Metrics
- ✅ All three subscription tiers successfully configured in Stripe
- ✅ Webhook processing handling 6+ event types with 100% reliability
- ✅ Plan enforcement preventing resource abuse across all feature areas
- ✅ Customer portal integration enabling self-service billing management
- ✅ Multi-tenant billing isolation verified across test scenarios
- ✅ Grandfathering system tested with custom pricing scenarios

## Future Considerations
- Implement dunning management for failed payment recovery
- Add usage-based billing for document storage overages
- Integrate with accounting systems (QuickBooks, Xero) for revenue recognition
- Implement annual billing discounts and promotional pricing
- Add more granular feature flags for plan customization
- Consider Stripe Tax for automated tax calculation and remittance

## References
- Story 0.5: Setup Subscription & Billing (Stripe)
- Stripe API Documentation
- Django-Tenants Multi-Tenancy Architecture
- PCI DSS Compliance Requirements