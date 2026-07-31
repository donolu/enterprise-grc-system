from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Risk, RiskAction, RiskCategory
from ..serializers import BulkRiskCreateSerializer, RiskActionBulkCreateSerializer

User = get_user_model()


class BulkErrorSanitisationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="bulk-security-user",
            email="bulk-security@example.com",
            password="testpass123",
        )
        self.category = RiskCategory.objects.create(name="Bulk Security")
        self.risk = Risk.objects.create(
            title="Existing risk",
            description="Existing risk description",
            category=self.category,
            risk_owner=self.user,
            impact=3,
            likelihood=3,
            status="assessed",
        )
        self.request = type("Request", (), {"user": self.user})()

    def test_bulk_risk_errors_do_not_expose_internal_exception_text(self):
        serializer = BulkRiskCreateSerializer(
            data={
                "category": self.category.pk,
                "risk_owner": self.user.pk,
                "risks": [
                    {
                        "title": "Sensitive failure",
                        "description": "This row will fail",
                    }
                ],
            },
            context={"request": self.request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        with patch.object(Risk.objects, "create", side_effect=RuntimeError("password=secret")):
            created_risks, errors = serializer.create_bulk_risks()

        self.assertEqual(created_risks, [])
        self.assertEqual(
            errors,
            [
                {
                    "index": 0,
                    "title": "Sensitive failure",
                    "error": "Unable to create risk.",
                }
            ],
        )

    def test_bulk_risk_action_errors_do_not_expose_internal_exception_text(self):
        serializer = RiskActionBulkCreateSerializer(
            data={
                "risk": self.risk.pk,
                "actions": [
                    {
                        "title": "Sensitive action failure",
                        "description": "This action will fail",
                        "due_date": (date.today() + timedelta(days=7)).isoformat(),
                    }
                ],
            },
            context={"request": self.request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        with patch.object(
            RiskAction.objects,
            "create",
            side_effect=RuntimeError("api_key=secret"),
        ):
            created_actions, errors = serializer.create_bulk_actions()

        self.assertEqual(created_actions, [])
        self.assertEqual(
            errors,
            [
                {
                    "index": 0,
                    "title": "Sensitive action failure",
                    "error": "Unable to create risk action.",
                }
            ],
        )
