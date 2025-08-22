from rest_framework import serializers
from core.models import Plan, Subscription


class PlanSerializer(serializers.ModelSerializer):
    """Serializer for subscription plans."""
    
    class Meta:
        model = Plan
        fields = [
            'id', 'name', 'slug', 'description', 'price_monthly',
            'max_users', 'max_documents', 'max_frameworks',
            'has_api_access', 'has_advanced_reporting', 'has_priority_support'
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for subscriptions."""
    
    plan = PlanSerializer(read_only=True)
    effective_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'plan', 'status', 'effective_price', 'is_active',
            'current_period_start', 'current_period_end',
            'trial_start', 'trial_end', 'seats_included',
            'is_grandfathered', 'created_at', 'updated_at'
        ]