import csv
import io
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from django.contrib.auth import get_user_model
from django.db.models import Max
from django_tenants.utils import schema_context, tenant_context
from django.utils import timezone

from billing.entitlements import MODULE_CATALOG
from core.models import AuditEvent, Document, Subscription, Tenant
from exports.models import TenantDataExport
from policies.models import PolicyAcknowledgment, PolicyDistribution
from training.models import CampaignDelivery, VideoView

User = get_user_model()


@dataclass(frozen=True)
class OperatorAnalyticsWindow:
    start_at: datetime
    end_at: datetime

    @classmethod
    def from_days(cls, days):
        safe_days = min(max(int(days or 90), 1), 365)
        end_at = timezone.now()
        return cls(start_at=end_at - timezone.timedelta(days=safe_days), end_at=end_at)


class OperatorProductAnalyticsService:
    """
    Aggregate product usage metrics for Axim operators without exposing tenant content.
    """

    def __init__(self, window=None):
        self.window = window or OperatorAnalyticsWindow.from_days(90)

    def build_dashboard(self):
        with schema_context('public'):
            tenants = list(Tenant.objects.order_by('name'))
            subscriptions = {
                subscription.tenant_id: subscription
                for subscription in Subscription.objects.select_related('tenant', 'plan')
            }

        tenant_summaries = []
        module_adoption = Counter()
        plan_counts = Counter()
        subscription_status_counts = Counter()
        aggregate_usage = Counter()
        active_tenant_count = 0
        collection_errors = []

        for tenant in tenants:
            subscription = subscriptions.get(tenant.id)
            enabled_modules = subscription.get_enabled_modules() if subscription else []
            module_adoption.update(enabled_modules)
            plan_slug = subscription.plan.slug if subscription else tenant.current_plan
            subscription_status = subscription.status if subscription else 'none'
            plan_counts[plan_slug] += 1
            subscription_status_counts[subscription_status] += 1

            try:
                tenant_usage = self._tenant_usage(tenant)
            except Exception as exc:  # pragma: no cover - defensive for partially migrated tenants
                collection_errors.append({'tenant_schema': tenant.schema_name, 'error': str(exc)})
                tenant_usage = self._empty_usage()

            aggregate_usage.update(tenant_usage['usage_counts'])
            if tenant_usage['last_activity_at']:
                active_tenant_count += 1

            tenant_summaries.append({
                'tenant_id': tenant.id,
                'tenant_slug': tenant.slug,
                'tenant_name': tenant.name,
                'schema_name': tenant.schema_name,
                'plan': plan_slug,
                'subscription_status': subscription_status,
                'enabled_modules': enabled_modules,
                'user_count': tenant_usage['user_count'],
                'usage_counts': tenant_usage['usage_counts'],
                'last_activity_at': tenant_usage['last_activity_at'],
            })

        total_tenants = len(tenants)
        return {
            'generated_at': timezone.now().isoformat(),
            'window': {
                'start_at': self.window.start_at.isoformat(),
                'end_at': self.window.end_at.isoformat(),
            },
            'summary': {
                'total_tenants': total_tenants,
                'active_tenants': active_tenant_count,
                'inactive_tenants': total_tenants - active_tenant_count,
                'trial_tenants': subscription_status_counts.get('trialing', 0),
                'paid_active_tenants': self._paid_active_count(subscriptions.values()),
                'past_due_tenants': subscription_status_counts.get('past_due', 0),
                'cancelled_tenants': subscription_status_counts.get('canceled', 0),
                'collection_error_count': len(collection_errors),
            },
            'plan_mix': dict(sorted(plan_counts.items())),
            'subscription_status_mix': dict(sorted(subscription_status_counts.items())),
            'module_adoption': [
                {
                    'module_key': module.key,
                    'module_label': module.label,
                    'tenant_count': module_adoption.get(module.key, 0),
                    'adoption_rate': self._percentage(module_adoption.get(module.key, 0), total_tenants),
                }
                for module in MODULE_CATALOG
            ],
            'usage_totals': dict(sorted(aggregate_usage.items())),
            'tenant_summaries': tenant_summaries,
            'privacy': {
                'tenant_content_excluded': True,
                'included_fields': [
                    'tenant identifiers',
                    'subscription status',
                    'enabled modules',
                    'aggregate counts',
                    'last activity timestamp',
                ],
            },
            'collection_errors': collection_errors,
        }

    def to_csv(self, dashboard):
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=[
                'tenant_id',
                'tenant_slug',
                'tenant_name',
                'schema_name',
                'plan',
                'subscription_status',
                'enabled_modules',
                'user_count',
                'document_uploads',
                'data_exports',
                'audit_events',
                'policy_acknowledgements',
                'policy_distributions',
                'training_deliveries',
                'training_views',
                'training_completions',
                'last_activity_at',
            ],
        )
        writer.writeheader()
        for summary in dashboard['tenant_summaries']:
            usage = summary['usage_counts']
            writer.writerow({
                'tenant_id': summary['tenant_id'],
                'tenant_slug': summary['tenant_slug'],
                'tenant_name': summary['tenant_name'],
                'schema_name': summary['schema_name'],
                'plan': summary['plan'],
                'subscription_status': summary['subscription_status'],
                'enabled_modules': ','.join(summary['enabled_modules']),
                'user_count': summary['user_count'],
                'document_uploads': usage['document_uploads'],
                'data_exports': usage['data_exports'],
                'audit_events': usage['audit_events'],
                'policy_acknowledgements': usage['policy_acknowledgements'],
                'policy_distributions': usage['policy_distributions'],
                'training_deliveries': usage['training_deliveries'],
                'training_views': usage['training_views'],
                'training_completions': usage['training_completions'],
                'last_activity_at': summary['last_activity_at'] or '',
            })
        return buffer.getvalue()

    def _tenant_usage(self, tenant):
        with tenant_context(tenant):
            last_activity = AuditEvent.objects.aggregate(last_activity=Max('at'))['last_activity']
            usage_counts = {
                'document_uploads': Document.objects.filter(uploaded_at__gte=self.window.start_at).count(),
                'data_exports': TenantDataExport.objects.filter(requested_at__gte=self.window.start_at).count(),
                'audit_events': AuditEvent.objects.filter(at__gte=self.window.start_at).count(),
                'policy_acknowledgements': PolicyAcknowledgment.objects.filter(
                    acknowledged_at__gte=self.window.start_at
                ).count(),
                'policy_distributions': PolicyDistribution.objects.filter(
                    distributed_at__gte=self.window.start_at
                ).count(),
                'training_deliveries': CampaignDelivery.objects.filter(sent_at__gte=self.window.start_at).count(),
                'training_views': VideoView.objects.filter(started_at__gte=self.window.start_at).count(),
                'training_completions': VideoView.objects.filter(
                    started_at__gte=self.window.start_at,
                    completed=True,
                ).count(),
            }
            return {
                'user_count': User.objects.filter(is_active=True).count(),
                'usage_counts': usage_counts,
                'last_activity_at': last_activity.isoformat() if last_activity else None,
            }

    def _empty_usage(self):
        return {
            'user_count': 0,
            'usage_counts': {
                'document_uploads': 0,
                'data_exports': 0,
                'audit_events': 0,
                'policy_acknowledgements': 0,
                'policy_distributions': 0,
                'training_deliveries': 0,
                'training_views': 0,
                'training_completions': 0,
            },
            'last_activity_at': None,
        }

    def _paid_active_count(self, subscriptions):
        return sum(
            1
            for subscription in subscriptions
            if subscription.status == 'active' and subscription.plan.price_monthly > 0
        )

    def _percentage(self, value, total):
        if not total:
            return 0.0
        return round((value / total) * 100, 1)
