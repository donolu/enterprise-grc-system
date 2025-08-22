"""
Health check views for monitoring and deployment verification.
"""

from django.http import JsonResponse
from django.views import View
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import os
import time
from datetime import datetime


class HealthCheckView(View):
    """
    Comprehensive health check endpoint for monitoring and deployment verification.
    """
    
    def get(self, request):
        """Return health status of the application and its dependencies."""
        health_data = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': getattr(settings, 'APP_VERSION', 'unknown'),
            'environment': os.environ.get('DJANGO_SETTINGS_MODULE', 'unknown'),
            'checks': {}
        }
        
        # Database check
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                health_data['checks']['database'] = {
                    'status': 'healthy',
                    'message': 'Database connection successful'
                }
        except Exception as e:
            health_data['status'] = 'unhealthy'
            health_data['checks']['database'] = {
                'status': 'unhealthy',
                'message': f'Database connection failed: {str(e)}'
            }
        
        # Cache check
        try:
            cache_key = 'health_check_test'
            cache_value = str(int(time.time()))
            cache.set(cache_key, cache_value, 10)
            cached_value = cache.get(cache_key)
            
            if cached_value == cache_value:
                health_data['checks']['cache'] = {
                    'status': 'healthy',
                    'message': 'Cache is working'
                }
            else:
                raise Exception('Cache value mismatch')
                
        except Exception as e:
            health_data['checks']['cache'] = {
                'status': 'degraded',
                'message': f'Cache check failed: {str(e)}'
            }
        
        # Storage check (Azure Blob Storage)
        try:
            from django.core.files.storage import default_storage
            if hasattr(default_storage, '_is_azure_available'):
                if default_storage._is_azure_available():
                    health_data['checks']['storage'] = {
                        'status': 'healthy',
                        'message': 'Azure Blob Storage is available'
                    }
                else:
                    health_data['checks']['storage'] = {
                        'status': 'degraded',
                        'message': 'Azure Blob Storage unavailable, using fallback'
                    }
            else:
                health_data['checks']['storage'] = {
                    'status': 'healthy',
                    'message': 'Local storage backend'
                }
        except Exception as e:
            health_data['checks']['storage'] = {
                'status': 'degraded',
                'message': f'Storage check failed: {str(e)}'
            }
        
        # Stripe connectivity check (basic)
        try:
            if hasattr(settings, 'STRIPE_SECRET_KEY') and settings.STRIPE_SECRET_KEY:
                # Don't make actual API call in health check, just verify config
                health_data['checks']['stripe'] = {
                    'status': 'healthy',
                    'message': 'Stripe configuration present'
                }
            else:
                health_data['checks']['stripe'] = {
                    'status': 'degraded', 
                    'message': 'Stripe not configured'
                }
        except Exception as e:
            health_data['checks']['stripe'] = {
                'status': 'degraded',
                'message': f'Stripe check failed: {str(e)}'
            }
        
        # Check if any critical systems are unhealthy
        critical_checks = ['database']
        for check_name in critical_checks:
            if health_data['checks'].get(check_name, {}).get('status') == 'unhealthy':
                health_data['status'] = 'unhealthy'
                break
        
        # Return appropriate HTTP status
        status_code = 200 if health_data['status'] in ['healthy', 'degraded'] else 503
        
        return JsonResponse(health_data, status=status_code)


class ReadinessCheckView(View):
    """
    Readiness check for Kubernetes/container orchestration.
    Only returns healthy when the app is fully ready to serve requests.
    """
    
    def get(self, request):
        """Return readiness status."""
        try:
            # Check database connectivity
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            
            # Check that essential tables exist (basic migration check)
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'core_tenant'
            """)
            
            if cursor.fetchone()[0] == 0:
                raise Exception("Core tables not found - migrations may not be complete")
            
            return JsonResponse({
                'status': 'ready',
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'not_ready',
                'message': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }, status=503)


class LivenessCheckView(View):
    """
    Liveness check for Kubernetes/container orchestration.
    Returns healthy if the process is running and not deadlocked.
    """
    
    def get(self, request):
        """Return liveness status."""
        return JsonResponse({
            'status': 'alive',
            'timestamp': datetime.utcnow().isoformat(),
            'pid': os.getpid()
        })


class StartupCheckView(View):
    """
    Startup check to verify the application started correctly.
    """
    
    def get(self, request):
        """Return startup verification."""
        startup_data = {
            'status': 'started',
            'timestamp': datetime.utcnow().isoformat(),
            'settings_module': os.environ.get('DJANGO_SETTINGS_MODULE'),
            'debug': settings.DEBUG,
            'database_name': settings.DATABASES['default']['NAME'],
            'cache_backend': settings.CACHES['default']['BACKEND'],
        }
        
        # Add version info if available
        if hasattr(settings, 'APP_VERSION'):
            startup_data['version'] = settings.APP_VERSION
        
        # Add deployment info if available
        if 'BUILD_ID' in os.environ:
            startup_data['build_id'] = os.environ['BUILD_ID']
        
        if 'DEPLOYMENT_TIME' in os.environ:
            startup_data['deployment_time'] = os.environ['DEPLOYMENT_TIME']
        
        return JsonResponse(startup_data)