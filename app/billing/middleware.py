from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
import json

from core.models import Tenant


class PlanEnforcementMiddleware(MiddlewareMixin):
    """
    Middleware to enforce plan limits across the application.
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.get_response = get_response
    
    def process_response(self, request, response):
        """Add plan information to API responses."""
        
        # Only add plan info to API responses for authenticated users
        if (hasattr(request, 'user') and 
            not isinstance(request.user, AnonymousUser) and
            request.path.startswith('/api/') and
            response.get('Content-Type', '').startswith('application/json')):
            
            try:
                tenant = Tenant.objects.get(schema_name=request.tenant.schema_name)
                subscription = getattr(tenant, 'subscription', None)
                
                if subscription and response.status_code == 200:
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
                                }
                            }
                    else:
                        # Regular Django JsonResponse
                        try:
                            content = json.loads(response.content.decode('utf-8'))
                            if isinstance(content, dict):
                                content['_plan_info'] = {
                                    'current_plan': subscription.plan.slug,
                                    'plan_name': subscription.plan.name,
                                    'is_active': subscription.is_active
                                }
                                response.content = json.dumps(content).encode('utf-8')
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            pass
                            
            except Exception:
                # Fail silently - don't break the response
                pass
        
        return response