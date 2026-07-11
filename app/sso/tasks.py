"""
Celery tasks for SSO operations.
"""

import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from .models import SSOSession, SSOAuditLog, SSOProvider
from .utils import cleanup_expired_sso_sessions

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_sessions():
    """
    Periodic task to cleanup expired SSO sessions.
    """
    try:
        count = cleanup_expired_sso_sessions()
        logger.info(f"Cleaned up {count} expired SSO sessions")
        return f"Cleaned up {count} expired SSO sessions"
    except Exception as e:
        logger.error(f"Failed to cleanup expired SSO sessions: {str(e)}")
        raise


@shared_task
def cleanup_old_audit_logs(days=90):
    """
    Periodic task to cleanup old SSO audit logs.
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=days)

        old_logs = SSOAuditLog.objects.filter(
            event_timestamp__lt=cutoff_date
        )

        count = old_logs.count()
        old_logs.delete()

        logger.info(f"Cleaned up {count} SSO audit logs older than {days} days")
        return f"Cleaned up {count} SSO audit logs older than {days} days"

    except Exception as e:
        logger.error(f"Failed to cleanup old audit logs: {str(e)}")
        raise


@shared_task
def generate_sso_usage_report():
    """
    Generate SSO usage statistics report.
    """
    try:
        from django.db.models import Count, Q

        # Calculate stats for the last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)

        stats = {
            'total_providers': SSOProvider.objects.filter(is_active=True).count(),
            'total_sessions': SSOSession.objects.filter(
                created_at__gte=thirty_days_ago
            ).count(),
            'active_sessions': SSOSession.objects.filter(
                status='active'
            ).count(),
            'login_attempts': SSOAuditLog.objects.filter(
                event_type='login_attempt',
                event_timestamp__gte=thirty_days_ago
            ).count(),
            'successful_logins': SSOAuditLog.objects.filter(
                event_type='login_success',
                event_timestamp__gte=thirty_days_ago
            ).count(),
            'failed_logins': SSOAuditLog.objects.filter(
                event_type='login_failure',
                event_timestamp__gte=thirty_days_ago
            ).count(),
            'jit_provisions': SSOAuditLog.objects.filter(
                event_type='jit_provisioning',
                event_timestamp__gte=thirty_days_ago
            ).count()
        }

        # Provider breakdown
        provider_stats = SSOProvider.objects.filter(
            is_active=True
        ).annotate(
            session_count=Count('ssosession', filter=Q(
                ssosession__created_at__gte=thirty_days_ago
            ))
        ).values('name', 'provider_type', 'session_count')

        report = {
            'period': '30 days',
            'generated_at': timezone.now().isoformat(),
            'summary': stats,
            'provider_breakdown': list(provider_stats)
        }

        logger.info("Generated SSO usage report")
        return report

    except Exception as e:
        logger.error(f"Failed to generate SSO usage report: {str(e)}")
        raise


@shared_task
def validate_sso_configurations():
    """
    Periodic task to validate all SSO provider configurations.
    """
    try:
        from .utils import validate_sso_configuration

        providers = SSOProvider.objects.filter(is_active=True)
        results = []

        for provider in providers:
            errors = validate_sso_configuration(provider)
            if errors:
                results.append({
                    'provider': provider.name,
                    'provider_id': str(provider.id),
                    'errors': errors
                })

                # Log configuration issues
                SSOAuditLog.log_event(
                    'configuration_change',
                    f"Configuration validation failed for {provider.name}",
                    sso_provider=provider,
                    success=False,
                    error_message='; '.join(errors),
                    details={'validation_errors': errors}
                )

        if results:
            logger.warning(f"Found configuration issues in {len(results)} SSO providers")
        else:
            logger.info("All SSO provider configurations are valid")

        return {
            'total_providers': providers.count(),
            'providers_with_issues': len(results),
            'issues': results
        }

    except Exception as e:
        logger.error(f"Failed to validate SSO configurations: {str(e)}")
        raise


@shared_task
def sync_sso_metadata():
    """
    Periodic task to sync and update SAML metadata URLs.
    """
    try:
        from .utils import generate_saml_metadata

        saml_providers = SSOProvider.objects.filter(
            provider_type='saml',
            is_active=True
        ).select_related('saml_config')

        updated_count = 0

        for provider in saml_providers:
            if hasattr(provider, 'saml_config'):
                saml_config = provider.saml_config

                # Generate SP URLs if missing
                if not saml_config.sp_entity_id:
                    saml_config.generate_sp_urls()
                    saml_config.save()
                    updated_count += 1

                    SSOAuditLog.log_event(
                        'configuration_change',
                        f"Updated SAML metadata for {provider.name}",
                        sso_provider=provider,
                        details={
                            'sp_entity_id': saml_config.sp_entity_id,
                            'sp_acs_url': saml_config.sp_acs_url,
                            'sp_sls_url': saml_config.sp_sls_url
                        }
                    )

        logger.info(f"Updated metadata for {updated_count} SAML providers")
        return f"Updated metadata for {updated_count} SAML providers"

    except Exception as e:
        logger.error(f"Failed to sync SSO metadata: {str(e)}")
        raise