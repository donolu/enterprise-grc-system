from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from core.models import Plan, Subscription
from .entitlements import get_module_catalog


class ModuleCatalogItemSerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    enabled = serializers.BooleanField(required=False)


class PlanSerializer(serializers.ModelSerializer):
    """Serializer for subscription plans."""
    module_catalog = serializers.SerializerMethodField()
    
    class Meta:
        model = Plan
        fields = [
            'id', 'name', 'slug', 'description', 'price_monthly',
            'max_users', 'max_documents', 'max_frameworks',
            'has_api_access', 'has_advanced_reporting', 'has_priority_support',
            'included_modules', 'module_catalog',
        ]

    @extend_schema_field(ModuleCatalogItemSerializer(many=True))
    def get_module_catalog(self, obj):
        return get_module_catalog(obj.get_included_modules())


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for subscriptions."""
    
    plan = PlanSerializer(read_only=True)
    effective_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    is_trial_active = serializers.BooleanField(read_only=True)
    enabled_module_keys = serializers.SerializerMethodField()
    module_catalog = serializers.SerializerMethodField()
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'plan', 'status', 'effective_price', 'is_active',
            'is_trial_active', 'enabled_modules', 'enabled_module_keys',
            'trial_module', 'module_catalog',
            'current_period_start', 'current_period_end',
            'trial_start', 'trial_end', 'seats_included',
            'is_grandfathered', 'created_at', 'updated_at'
        ]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_enabled_module_keys(self, obj):
        return obj.get_enabled_modules()

    @extend_schema_field(ModuleCatalogItemSerializer(many=True))
    def get_module_catalog(self, obj):
        return get_module_catalog(obj.get_enabled_modules())
