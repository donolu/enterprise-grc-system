from typing import Dict, Any, Optional, Tuple
from django.contrib.auth import get_user_model
from core.models import Tenant, Plan, Subscription, Document

User = get_user_model()


class PlanEnforcementService:
    """
    Service class for checking plan limits and features.
    """
    
    @staticmethod
    def get_tenant_subscription(tenant: Tenant) -> Optional[Subscription]:
        """Get tenant's current subscription."""
        return getattr(tenant, 'subscription', None)
    
    @staticmethod
    def check_feature_access(tenant: Tenant, feature: str) -> Tuple[bool, Optional[str]]:
        """
        Check if tenant has access to a specific feature.
        
        Returns:
            Tuple of (has_access, error_message)
        """
        subscription = PlanEnforcementService.get_tenant_subscription(tenant)
        
        if not subscription:
            return False, "No active subscription found"
        
        if not subscription.is_active:
            return False, "Subscription is not active"
        
        plan = subscription.plan
        
        if not hasattr(plan, feature):
            return False, f"Unknown feature: {feature}"
        
        has_feature = getattr(plan, feature, False)
        if not has_feature:
            return False, f"Feature '{feature}' not available in {plan.name} plan"
        
        return True, None
    
    @staticmethod
    def check_user_limit(tenant: Tenant) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if tenant can add more users.
        
        Returns:
            Tuple of (can_add_user, usage_info)
        """
        subscription = PlanEnforcementService.get_tenant_subscription(tenant)
        
        if not subscription:
            return False, {"error": "No active subscription"}
        
        # Count current users in tenant schema (requires tenant context)
        # This would need to be called within tenant context
        current_users = User.objects.count()
        max_users = subscription.get_effective_user_limit()
        
        usage_info = {
            "current_users": current_users,
            "max_users": max_users,
            "users_remaining": max_users - current_users,
            "at_limit": current_users >= max_users
        }
        
        can_add = current_users < max_users
        if not can_add:
            usage_info["error"] = f"User limit reached. Plan allows {max_users} users."
        
        return can_add, usage_info
    
    @staticmethod
    def check_document_limit(tenant: Tenant) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if tenant can upload more documents.
        
        Returns:
            Tuple of (can_add_document, usage_info)
        """
        subscription = PlanEnforcementService.get_tenant_subscription(tenant)
        
        if not subscription:
            return False, {"error": "No active subscription"}
        
        # Count current documents in tenant schema
        current_docs = Document.objects.count()
        max_docs = subscription.get_effective_document_limit()
        
        usage_info = {
            "current_documents": current_docs,
            "max_documents": max_docs,
            "documents_remaining": max_docs - current_docs,
            "at_limit": current_docs >= max_docs
        }
        
        can_add = current_docs < max_docs
        if not can_add:
            usage_info["error"] = f"Document limit reached. Plan allows {max_docs} documents."
        
        return can_add, usage_info
    
    @staticmethod
    def get_plan_usage_summary(tenant: Tenant) -> Dict[str, Any]:
        """
        Get comprehensive usage summary for tenant's plan.
        """
        subscription = PlanEnforcementService.get_tenant_subscription(tenant)
        
        if not subscription:
            return {"error": "No active subscription"}
        
        plan = subscription.plan
        
        # This would need to be called within tenant context for accurate counts
        user_count = User.objects.count()
        doc_count = Document.objects.count()
        
        return {
            "subscription": {
                "plan_name": plan.name,
                "plan_slug": plan.slug,
                "status": subscription.status,
                "is_active": subscription.is_active,
                "effective_price": float(subscription.effective_price),
            },
            "limits": {
                "users": {
                    "current": user_count,
                    "max": subscription.get_effective_user_limit(),
                    "remaining": subscription.get_effective_user_limit() - user_count,
                    "at_limit": user_count >= subscription.get_effective_user_limit(),
                    "has_override": subscription.custom_max_users is not None
                },
                "documents": {
                    "current": doc_count,
                    "max": subscription.get_effective_document_limit(),
                    "remaining": subscription.get_effective_document_limit() - doc_count,
                    "at_limit": doc_count >= subscription.get_effective_document_limit(),
                    "has_override": subscription.custom_max_documents is not None
                },
                "frameworks": {
                    "max": subscription.get_effective_framework_limit(),
                    "has_override": subscription.custom_max_frameworks is not None
                }
            },
            "features": {
                "api_access": plan.has_api_access,
                "advanced_reporting": plan.has_advanced_reporting,
                "priority_support": plan.has_priority_support
            }
        }
    
    @staticmethod
    def get_upgrade_recommendations(tenant: Tenant) -> Dict[str, Any]:
        """
        Get upgrade recommendations based on current usage.
        """
        subscription = PlanEnforcementService.get_tenant_subscription(tenant)
        
        if not subscription:
            return {"error": "No active subscription"}
        
        current_plan = subscription.plan
        user_count = User.objects.count()
        doc_count = Document.objects.count()
        
        recommendations = []
        
        # Check if approaching limits (using effective limits)
        effective_user_limit = subscription.get_effective_user_limit()
        effective_doc_limit = subscription.get_effective_document_limit()
        
        if user_count >= effective_user_limit * 0.8:
            recommendations.append({
                "type": "user_limit",
                "message": "Approaching user limit",
                "current": user_count,
                "limit": effective_user_limit,
                "has_custom_override": subscription.custom_max_users is not None
            })
        
        if doc_count >= effective_doc_limit * 0.8:
            recommendations.append({
                "type": "document_limit", 
                "message": "Approaching document limit",
                "current": doc_count,
                "limit": effective_doc_limit,
                "has_custom_override": subscription.custom_max_documents is not None
            })
        
        # Suggest upgrades based on missing features
        next_plan = None
        if current_plan.slug == 'free':
            next_plan = Plan.objects.filter(slug='basic').first()
        elif current_plan.slug == 'basic':
            next_plan = Plan.objects.filter(slug='enterprise').first()
        
        return {
            "current_plan": current_plan.slug,
            "recommendations": recommendations,
            "suggested_upgrade": {
                "plan": next_plan.slug if next_plan else None,
                "plan_name": next_plan.name if next_plan else None,
                "price": float(next_plan.price_monthly) if next_plan else None
            } if next_plan else None
        }