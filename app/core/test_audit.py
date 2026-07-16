from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from core.audit import build_audit_details, log_audit_event
from core.models import AuditEvent, Plan

User = get_user_model()


class AuditEventStandardTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='auditor',
            email='auditor@example.com',
            password='testpass123',
        )
        self.plan = Plan.objects.create(
            name='Enterprise',
            slug='enterprise',
            price_monthly=199,
        )

    def test_build_audit_details_uses_standard_payload_shape(self):
        request = RequestFactory().post(
            '/api/example/',
            HTTP_USER_AGENT='UnitTest/1.0',
            HTTP_X_FORWARDED_FOR='203.0.113.10, 10.0.0.1',
            HTTP_X_REQUEST_ID='req-123',
        )

        details = build_audit_details(
            event='PLAN_UPDATED',
            actor=self.user,
            target=self.plan,
            object_display='Enterprise plan',
            previous={'price_monthly': '99.00'},
            new={'price_monthly': '199.00'},
            reason='annual pricing update',
            request=request,
            source={'type': 'admin', 'reference': 'plans/change'},
            details={'legacy_field': 'kept'},
        )

        self.assertEqual(details['actor']['id'], str(self.user.id))
        self.assertEqual(details['actor']['email'], 'auditor@example.com')
        self.assertEqual(details['actor']['type'], 'user')
        self.assertEqual(details['object']['type'], 'core.Plan')
        self.assertEqual(details['object']['id'], str(self.plan.id))
        self.assertEqual(details['object']['display'], 'Enterprise plan')
        self.assertEqual(details['event'], 'PLAN_UPDATED')
        self.assertEqual(details['previous'], {'price_monthly': '99.00'})
        self.assertEqual(details['new'], {'price_monthly': '199.00'})
        self.assertEqual(details['reason'], 'annual pricing update')
        self.assertEqual(details['request']['ip'], '203.0.113.10')
        self.assertEqual(details['request']['user_agent'], 'UnitTest/1.0')
        self.assertEqual(details['request']['request_id'], 'req-123')
        self.assertEqual(details['source'], {'type': 'admin', 'reference': 'plans/change'})
        self.assertEqual(details['legacy_field'], 'kept')

    def test_object_display_is_not_derived_from_model_string(self):
        details = build_audit_details(
            event='PLAN_UPDATED',
            actor=self.user,
            target=self.plan,
        )

        self.assertEqual(details['object']['type'], 'core.Plan')
        self.assertEqual(details['object']['id'], str(self.plan.id))
        self.assertEqual(details['object']['display'], '')
        self.assertNotIn(str(self.plan), str(details))

    def test_log_audit_event_persists_standard_event(self):
        event = log_audit_event(
            event='PLAN_UPDATED',
            actor=self.user,
            target=self.plan,
            object_display='Enterprise plan',
            new={'price_monthly': '199.00'},
        )

        stored = AuditEvent.objects.get(pk=event.pk)
        self.assertEqual(stored.user, self.user)
        self.assertEqual(stored.event, 'PLAN_UPDATED')
        self.assertEqual(stored.details['object']['type'], 'core.Plan')
        self.assertEqual(stored.details['object']['id'], str(self.plan.id))
        self.assertEqual(stored.details['new'], {'price_monthly': '199.00'})

    def test_system_actor_is_used_when_no_user_is_available(self):
        details = build_audit_details(event='WORKER_COMPLETED')

        self.assertEqual(details['actor'], {'id': None, 'email': 'system', 'type': 'system'})
        self.assertEqual(details['request'], {'ip': '', 'user_agent': '', 'request_id': ''})
        self.assertEqual(details['source'], {'type': '', 'reference': ''})

    def test_anonymous_user_is_treated_as_system_actor(self):
        event = log_audit_event(event='ANONYMOUS_ATTEMPT', actor=AnonymousUser())

        self.assertIsNone(event.user)
        self.assertEqual(event.details['actor'], {'id': None, 'email': 'system', 'type': 'system'})
