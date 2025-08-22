from functools import wraps
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from rest_framework import status
from rest_framework.response import Response

from core.models import Tenant, User, Document


def plan_required(plan_feature=None, min_plan=None, feature_check=None):
    """
    Decorator to enforce plan limits and features.
    
    Args:
        plan_feature: Required plan feature (e.g., 'has_api_access')
        min_plan: Minimum required plan (e.g., 'basic', 'enterprise')
        feature_check: Custom function to check feature limits
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Skip check if user is not authenticated
            if not request.user.is_authenticated:
                return view_func(request, *args, **kwargs)
            
            try:
                tenant = Tenant.objects.get(schema_name=request.tenant.schema_name)
                subscription = getattr(tenant, 'subscription', None)
                
                if not subscription:
                    return JsonResponse(
                        {'error': 'No active subscription found'}, 
                        status=403
                    )
                
                plan = subscription.plan
                
                # Check minimum plan requirement
                if min_plan:
                    plan_hierarchy = {'free': 0, 'basic': 1, 'enterprise': 2}
                    required_level = plan_hierarchy.get(min_plan, 0)
                    current_level = plan_hierarchy.get(plan.slug, 0)
                    
                    if current_level < required_level:
                        return JsonResponse({
                            'error': f'This feature requires {min_plan.title()} plan or higher',
                            'current_plan': plan.slug,
                            'required_plan': min_plan,
                            'upgrade_needed': True
                        }, status=403)
                
                # Check specific plan feature
                if plan_feature:
                    if not getattr(plan, plan_feature, False):
                        return JsonResponse({
                            'error': f'This feature is not available in your current plan',
                            'current_plan': plan.slug,
                            'feature_required': plan_feature,
                            'upgrade_needed': True
                        }, status=403)
                
                # Custom feature check
                if feature_check:
                    result = feature_check(request, tenant, subscription, plan)
                    if result is not True:
                        return JsonResponse(result, status=403)
                
                return view_func(request, *args, **kwargs)
                
            except Exception as e:
                return JsonResponse(
                    {'error': 'Failed to verify subscription'}, 
                    status=500
                )
        
        return _wrapped_view
    return decorator


def check_user_limit(request, tenant, subscription, plan):
    """Check if tenant has exceeded user limit."""
    user_count = User.objects.count()
    if user_count >= plan.max_users:
        return {
            'error': f'User limit exceeded. Your plan allows {plan.max_users} users.',
            'current_users': user_count,
            'max_users': plan.max_users,
            'upgrade_needed': True
        }
    return True


def check_document_limit(request, tenant, subscription, plan):
    """Check if tenant has exceeded document limit."""
    doc_count = Document.objects.count()
    if doc_count >= plan.max_documents:
        return {
            'error': f'Document limit exceeded. Your plan allows {plan.max_documents} documents.',
            'current_documents': doc_count,
            'max_documents': plan.max_documents,
            'upgrade_needed': True
        }
    return True


# Pre-built decorators for common checks
require_api_access = plan_required(plan_feature='has_api_access')
require_basic_plan = plan_required(min_plan='basic')
require_enterprise_plan = plan_required(min_plan='enterprise')
require_advanced_reporting = plan_required(plan_feature='has_advanced_reporting')
check_user_limits = plan_required(feature_check=check_user_limit)
check_document_limits = plan_required(feature_check=check_document_limit)