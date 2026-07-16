from __future__ import annotations

from collections.abc import Mapping

from django_tenants.utils import tenant_context

from core.audit import changed_values, log_audit_event, snapshot_model


SUBSCRIPTION_FIELDS = (
    'plan_id',
    'status',
    'current_period_start',
    'current_period_end',
    'trial_start',
    'trial_end',
    'custom_price',
    'is_grandfathered',
    'seats_included',
    'custom_max_users',
    'custom_max_documents',
    'custom_max_frameworks',
    'custom_max_storage_gb',
    'enabled_modules',
    'trial_module',
)
LIMIT_OVERRIDE_FIELDS = (
    'limit_type',
    'current_limit',
    'requested_limit',
    'urgency',
    'temporary',
    'expires_at',
    'status',
    'requested_by',
    'first_approver',
    'first_approved_at',
    'second_approver',
    'second_approved_at',
    'final_decision_by',
    'final_decision_at',
    'rejection_reason',
    'applied_at',
    'applied_by',
)


def snapshot_subscription(subscription):
    payload = snapshot_model(subscription, SUBSCRIPTION_FIELDS)
    payload['plan_slug'] = subscription.plan.slug
    payload['plan_name'] = subscription.plan.name
    payload['effective_price'] = str(subscription.effective_price)
    payload['stripe_customer_present'] = bool(subscription.stripe_customer_id)
    payload['stripe_subscription_present'] = bool(subscription.stripe_subscription_id)
    return payload


def snapshot_limit_override(override_request):
    payload = snapshot_model(override_request, LIMIT_OVERRIDE_FIELDS)
    payload['subscription_id'] = override_request.subscription_id
    payload['tenant_schema'] = override_request.subscription.tenant.schema_name
    return payload


def audit_subscription_change(
    *,
    event: str,
    subscription,
    actor=None,
    request=None,
    previous: Mapping | None = None,
    new: Mapping | None = None,
    reason: str = '',
    source: Mapping | None = None,
    details: Mapping | None = None,
):
    with tenant_context(subscription.tenant):
        return log_audit_event(
            event=event,
            actor=actor,
            target=subscription,
            object_display=subscription_display(subscription),
            previous=previous,
            new=new,
            reason=reason,
            request=request,
            source=source or {'type': 'api', 'reference': ''},
            details=details,
        )


def audit_limit_override_change(
    *,
    event: str,
    override_request,
    actor=None,
    request=None,
    previous: Mapping | None = None,
    new: Mapping | None = None,
    reason: str = '',
    source: Mapping | None = None,
    details: Mapping | None = None,
):
    with tenant_context(override_request.subscription.tenant):
        return log_audit_event(
            event=event,
            actor=actor,
            target=override_request,
            object_display=limit_override_display(override_request),
            previous=previous,
            new=new,
            reason=reason,
            request=request,
            source=source or {'type': 'api', 'reference': ''},
            details=details,
        )


def billing_changed_values(previous, new):
    return changed_values(previous, new)


def subscription_display(subscription) -> str:
    return f'subscription:{subscription.pk}'


def limit_override_display(override_request) -> str:
    return f'limit-override:{override_request.pk}'
