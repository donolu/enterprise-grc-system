from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from compliance.models import GovernanceArtefact
from core.identifiers import save_with_generated_identifier
from policies.models import Policy, PolicyCategory
from risk.models import Risk

User = get_user_model()


class GeneratedIdentifierTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="identifier.owner",
            email="identifier.owner@example.com",
            password="testpass123",
        )

    def test_generated_identifier_retries_after_unique_collision(self):
        year = timezone.now().year
        existing_id = f"RISK-{year}-0001"
        next_id = f"RISK-{year}-0002"
        Risk.objects.create(
            risk_id=existing_id,
            title="Existing risk",
            description="Existing risk description.",
            impact=3,
            likelihood=3,
            risk_owner=self.user,
            created_by=self.user,
        )

        with patch.object(Risk, "_generate_risk_id", side_effect=[existing_id, next_id]):
            risk = Risk.objects.create(
                title="Concurrent risk",
                description="Risk created while another worker claimed the first ID.",
                impact=4,
                likelihood=3,
                risk_owner=self.user,
                created_by=self.user,
            )

        self.assertEqual(risk.risk_id, next_id)

    def test_generated_identifier_does_not_retry_unrelated_integrity_error(self):
        generated_ids: list[str] = []
        risk = Risk(
            title="Invalid concurrent risk",
            description="Risk with an unrelated integrity failure.",
            impact=4,
            likelihood=3,
            risk_owner=self.user,
            created_by=self.user,
        )

        def generate_id() -> str:
            identifier = f"RISK-{timezone.now().year}-0099"
            generated_ids.append(identifier)
            return identifier

        def fail_save() -> None:
            raise IntegrityError("unrelated constraint failure")

        with self.assertRaises(IntegrityError):
            save_with_generated_identifier(risk, "risk_id", generate_id, fail_save)

        self.assertEqual(generated_ids, [f"RISK-{timezone.now().year}-0099"])

    def test_identifier_generation_uses_highest_suffix_when_sequence_has_gaps(self):
        year = timezone.now().year
        GovernanceArtefact.objects.create(
            artefact_id=f"GOV-{year}-0003",
            title="Existing scope document",
            artefact_type="scope_document",
            owner=self.user,
            created_by=self.user,
        )

        artefact = GovernanceArtefact.objects.create(
            title="Next scope document",
            artefact_type="scope_document",
            owner=self.user,
            created_by=self.user,
        )

        self.assertEqual(artefact.artefact_id, f"GOV-{year}-0004")

    def test_policy_code_generation_uses_highest_category_suffix(self):
        category = PolicyCategory.objects.create(name="Security")
        Policy.objects.create(
            policy_code="POL-SEC-003",
            title="Existing information security policy",
            category=category,
            owner=self.user,
            created_by=self.user,
        )

        policy = Policy.objects.create(
            title="Acceptable use policy",
            category=category,
            owner=self.user,
            created_by=self.user,
        )

        self.assertEqual(policy.policy_code, "POL-SEC-004")
