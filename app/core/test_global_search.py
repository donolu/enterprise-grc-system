import pytest
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context, tenant_context
from rest_framework import status

from core.models import Plan, Subscription
from risk.models import Risk, RiskCategory
from training.models import TrainingCategory, TrainingVideo
from vendors.models import Vendor


User = get_user_model()


@pytest.mark.django_db
class TestGlobalSearchAPI:
    def test_returns_only_current_tenant_published_records(
        self, api_client, test_tenant, test_user
    ):
        with tenant_context(test_tenant):
            category = RiskCategory.objects.create(name="Search category")
            risk = Risk.objects.create(
                risk_id="RISK-NEEDLE",
                title="Needle risk",
                description="A searchable risk.",
                category=category,
                impact=3,
                likelihood=3,
                created_by=test_user,
            )
            vendor = Vendor.objects.create(name="Needle vendor", created_by=test_user)
            training_category = TrainingCategory.objects.create(name="Search training")
            video = TrainingVideo.objects.create(
                title="Needle training",
                description="A searchable training video.",
                category=training_category,
                video_url="https://example.test/needle",
                created_by=test_user,
                is_published=True,
            )
            TrainingVideo.objects.create(
                title="Hidden needle training",
                description="This must not be searchable.",
                category=training_category,
                video_url="https://example.test/hidden",
                created_by=test_user,
                is_published=False,
            )

        api_client.defaults["HTTP_HOST"] = f"{test_tenant.schema_name}.localhost"
        api_client.force_authenticate(user=test_user)

        response = api_client.get("/api/search/", {"q": "needle"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["query"] == "needle"
        assert response.data["results"] == [
            {
                "id": str(risk.id),
                "entity_type": "risk",
                "title": "Needle risk",
                "context": "RISK-NEEDLE",
                "href": f"/risk/{risk.id}",
            },
            {
                "id": str(vendor.id),
                "entity_type": "vendor",
                "title": "Needle vendor",
                "context": vendor.vendor_id,
                "href": f"/vendors/{vendor.id}",
            },
            {
                "id": str(video.id),
                "entity_type": "training",
                "title": "Needle training",
                "context": "Search training",
                "href": f"/training/video/{video.id}",
            },
        ]

    def test_respects_subscription_module_entitlements(self, api_client, test_tenant, test_user):
        with schema_context("public"):
            plan = Plan.objects.create(
                name="Risk only",
                slug="risk-only",
                price_monthly=10,
                included_modules=["risk"],
            )
            Subscription.objects.create(tenant=test_tenant, plan=plan, status="active")

        with tenant_context(test_tenant):
            category = RiskCategory.objects.create(name="Entitlement category")
            Risk.objects.create(
                risk_id="RISK-ACCESS",
                title="Access needle risk",
                description="A searchable risk.",
                category=category,
                impact=2,
                likelihood=2,
                created_by=test_user,
            )
            Vendor.objects.create(name="Access needle vendor", created_by=test_user)

        api_client.defaults["HTTP_HOST"] = f"{test_tenant.schema_name}.localhost"
        api_client.force_authenticate(user=test_user)

        response = api_client.get("/api/search/", {"q": "needle"})

        assert response.status_code == status.HTTP_200_OK
        assert [result["entity_type"] for result in response.data["results"]] == ["risk"]

    @pytest.mark.parametrize("query", ["", "n", "x" * 101])
    def test_rejects_invalid_query_lengths(self, api_client, test_tenant, test_user, query):
        api_client.defaults["HTTP_HOST"] = f"{test_tenant.schema_name}.localhost"
        api_client.force_authenticate(user=test_user)

        response = api_client.get("/api/search/", {"q": query})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
