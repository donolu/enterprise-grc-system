from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
import json

from .entitlements import get_module_catalog, get_module_for_path
from .tenant_access import get_public_tenant


class PlanEnforcementMiddleware(MiddlewareMixin):
    """
    Middleware to enforce plan limits across the application.
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.get_response = get_response

    def process_request(self, request):
        """Block subscribed tenants from accessing modules outside their entitlement."""
        module_key = get_module_for_path(request.path)
        if not module_key or not hasattr(request, 'tenant'):
            return None
        if request.path.startswith('/api/analytics/operator/'):
            return None

        try:
            tenant = get_public_tenant(request.tenant.schema_name)
            subscription = getattr(tenant, 'subscription', None)
        except Exception:
            return None

        # Legacy/dev tenants may not have gone through billing setup yet. Once a
        # subscription exists, module entitlements are authoritative.
        if not subscription:
            return None

        if subscription.has_module_access(module_key):
            return None

        return JsonResponse(
            {
                'detail': 'This module is not enabled for the current subscription.',
                'code': 'module_not_enabled',
                'module': module_key,
                'enabled_modules': subscription.get_enabled_modules(),
                'trial_module': subscription.trial_module,
                'subscription_status': subscription.status,
                'upgrade_needed': subscription.plan.slug != 'enterprise',
            },
            status=403,
        )
    
    def process_response(self, request, response):
        """Add plan information to API responses."""
        
        # Only add plan info to API responses for authenticated users
        if (hasattr(request, 'user') and 
            not isinstance(request.user, AnonymousUser) and
            request.path.startswith('/api/') and
            response.get('Content-Type', '').startswith('application/json')):
            
            try:
                tenant = get_public_tenant(request.tenant.schema_name)
                subscription = getattr(tenant, 'subscription', None)
                
                if subscription and response.status_code == 200:
                    enabled_modules = subscription.get_enabled_modules()
                    # Parse existing response
                    if hasattr(response, 'data'):
                        # DRF Response
                        if isinstance(response.data, dict):
                            response.data['_plan_info'] = {
                                'current_plan': subscription.plan.slug,
                                'plan_name': subscription.plan.name,
                                'is_active': subscription.is_active,
                                'limits': {
                                    'max_users': subscription.plan.max_users,
                                    'max_documents': subscription.plan.max_documents,
                                    'max_frameworks': subscription.plan.max_frameworks,
                                },
                                'features': {
                                    'has_api_access': subscription.plan.has_api_access,
                                    'has_advanced_reporting': subscription.plan.has_advanced_reporting,
                                    'has_priority_support': subscription.plan.has_priority_support,
                                },
                                'entitlements': {
                                    'enabled_modules': enabled_modules,
                                    'trial_module': subscription.trial_module,
                                    'module_catalog': get_module_catalog(enabled_modules),
                                },
                            }
                    else:
                        # Regular Django JsonResponse
                        try:
                            content = json.loads(response.content.decode('utf-8'))
                            if isinstance(content, dict):
                                content['_plan_info'] = {
                                    'current_plan': subscription.plan.slug,
                                    'plan_name': subscription.plan.name,
                                    'is_active': subscription.is_active,
                                    'entitlements': {
                                        'enabled_modules': enabled_modules,
                                    },
                                }
                                response.content = json.dumps(content).encode('utf-8')
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            pass
                            
            except Exception:
                # Fail silently - don't break the response
                pass
        
        return response
