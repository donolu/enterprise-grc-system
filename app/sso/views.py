"""
SSO Views for SAML and OAuth authentication flows.
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import SSOProvider, SAMLProvider, SSOSession, SSOAuditLog
from .backends import SAMLBackend
from .utils import get_tenant_from_request, generate_saml_metadata

logger = logging.getLogger(__name__)


def sso_login_select(request):
    """
    Show available SSO providers for the tenant.
    """
    tenant = get_tenant_from_request(request)
    if not tenant:
        return HttpResponseBadRequest("Tenant not found")

    sso_providers = SSOProvider.objects.filter(
        tenant=tenant,
        is_active=True
    ).select_related('saml_config', 'oauth_config')

    context = {
        'sso_providers': sso_providers,
        'tenant': tenant
    }

    return render(request, 'sso/login_select.html', context)


def saml_login(request, provider_id):
    """
    Initiate SAML authentication.
    """
    tenant = get_tenant_from_request(request)
    if not tenant:
        return HttpResponseBadRequest("Tenant not found")

    try:
        sso_provider = SSOProvider.objects.get(
            id=provider_id,
            tenant=tenant,
            is_active=True,
            provider_type='saml'
        )

        if not hasattr(sso_provider, 'saml_config'):
            logger.error(f"SAML config not found for provider {sso_provider.name}")
            return HttpResponseBadRequest("SAML configuration not found")

        # Initialize SAML auth
        saml_backend = SAMLBackend()
        saml_auth = saml_backend._init_saml_auth(request, sso_provider.saml_config)

        if not saml_auth:
            return HttpResponseBadRequest("Failed to initialize SAML authentication")

        # Log login attempt
        SSOAuditLog.log_event(
            'login_attempt',
            f"SAML login initiated for provider {sso_provider.name}",
            sso_provider=sso_provider,
            request=request
        )

        # Redirect to IdP
        return redirect(saml_auth.login())

    except SSOProvider.DoesNotExist:
        logger.error(f"SSO provider {provider_id} not found")
        return HttpResponseBadRequest("SSO provider not found")
    except Exception as e:
        logger.error(f"SAML login error: {str(e)}")
        return HttpResponseBadRequest("SAML login failed")


@csrf_exempt
@require_http_methods(["POST"])
def saml_acs(request, provider_id):
    """
    SAML Assertion Consumer Service - handle SAML response from IdP.
    """
    tenant = get_tenant_from_request(request)
    if not tenant:
        return HttpResponseBadRequest("Tenant not found")

    try:
        # Authenticate user via SAML backend
        backend = SAMLBackend()
        user = backend.authenticate(
            request,
            saml_response=request.POST.get('SAMLResponse'),
            saml_provider_id=provider_id
        )

        if user:
            # Log in the user
            login(request, user, backend='sso.backends.SAMLBackend')

            # Redirect to next URL or dashboard
            next_url = request.session.get('next_url', '/')
            if 'next_url' in request.session:
                del request.session['next_url']

            return redirect(next_url)
        else:
            # Authentication failed
            return render(request, 'sso/login_error.html', {
                'error': 'SAML authentication failed'
            })

    except Exception as e:
        logger.error(f"SAML ACS error: {str(e)}")
        return render(request, 'sso/login_error.html', {
            'error': 'An error occurred during authentication'
        })


def saml_sls(request, provider_id):
    """
    SAML Single Logout Service.
    """
    tenant = get_tenant_from_request(request)
    if not tenant:
        return HttpResponseBadRequest("Tenant not found")

    try:
        sso_provider = SSOProvider.objects.get(
            id=provider_id,
            tenant=tenant,
            is_active=True,
            provider_type='saml'
        )

        # Get SSO session
        sso_session_id = request.session.get('sso_session_id')
        if sso_session_id:
            try:
                sso_session = SSOSession.objects.get(id=sso_session_id)
                sso_session.status = 'logged_out'
                sso_session.save()

                SSOAuditLog.log_event(
                    'logout',
                    f"User {request.user.email} logged out via SAML SLS",
                    sso_provider=sso_provider,
                    user=request.user,
                    request=request
                )
            except SSOSession.DoesNotExist:
                pass

        # Log out the user
        logout(request)

        return redirect('/')

    except SSOProvider.DoesNotExist:
        logger.error(f"SSO provider {provider_id} not found")
        return HttpResponseBadRequest("SSO provider not found")


def saml_metadata(request, provider_id):
    """
    Generate and serve SAML metadata for Service Provider.
    """
    tenant = get_tenant_from_request(request)
    if not tenant:
        return HttpResponseBadRequest("Tenant not found")

    try:
        sso_provider = SSOProvider.objects.get(
            id=provider_id,
            tenant=tenant,
            provider_type='saml'
        )

        metadata_xml = generate_saml_metadata(sso_provider)
        if not metadata_xml:
            return HttpResponseBadRequest("Failed to generate metadata")

        return HttpResponse(
            metadata_xml,
            content_type='application/xml'
        )

    except SSOProvider.DoesNotExist:
        return HttpResponseBadRequest("SSO provider not found")


@login_required
def sso_logout(request):
    """
    Initiate SSO logout if user authenticated via SSO.
    """
    sso_session_id = request.session.get('sso_session_id')

    if sso_session_id:
        try:
            sso_session = SSOSession.objects.get(id=sso_session_id)
            sso_provider = sso_session.sso_provider

            # Update session status
            sso_session.status = 'logged_out'
            sso_session.save()

            # Log logout
            SSOAuditLog.log_event(
                'logout',
                f"User {request.user.email} initiated logout",
                sso_provider=sso_provider,
                user=request.user,
                request=request
            )

            # For SAML, we could initiate SLO here
            if sso_provider.provider_type == 'saml':
                # Could redirect to SAML SLO endpoint
                pass

        except SSOSession.DoesNotExist:
            pass

    # Standard logout
    logout(request)
    return redirect('/')


@login_required
def sso_profile(request):
    """
    Show user's SSO profile and session information.
    """
    sso_sessions = SSOSession.objects.filter(
        user=request.user
    ).select_related('sso_provider').order_by('-created_at')[:10]

    context = {
        'sso_sessions': sso_sessions
    }

    return render(request, 'sso/profile.html', context)


def sso_status(request):
    """
    API endpoint to check SSO status and configuration.
    """
    tenant = get_tenant_from_request(request)
    if not tenant:
        return JsonResponse({'error': 'Tenant not found'}, status=400)

    sso_providers = SSOProvider.objects.filter(
        tenant=tenant,
        is_active=True
    ).values('id', 'name', 'provider_type', 'is_primary')

    return JsonResponse({
        'sso_enabled': sso_providers.exists(),
        'providers': list(sso_providers),
        'enforce_sso': any(p.get('enforce_sso') for p in sso_providers)
    })


# OAuth views
def oauth_login(request, provider_id):
    """
    Initiate OAuth authentication.
    """
    tenant = get_tenant_from_request(request)
    if not tenant:
        return HttpResponseBadRequest("Tenant not found")

    try:
        sso_provider = SSOProvider.objects.get(
            id=provider_id,
            tenant=tenant,
            is_active=True,
            provider_type='oauth'
        )

        if not hasattr(sso_provider, 'oauth_config'):
            logger.error(f"OAuth config not found for provider {sso_provider.name}")
            return HttpResponseBadRequest("OAuth configuration not found")

        from .oauth_backends import OAuthClient

        # Generate state parameter for CSRF protection
        import secrets
        state = secrets.token_urlsafe(32)
        request.session['oauth_state'] = state
        request.session['oauth_provider_id'] = str(provider_id)

        # Build authorization URL
        auth_url = OAuthClient.build_authorization_url(
            sso_provider.oauth_config,
            request,
            state=state
        )

        # Log login attempt
        SSOAuditLog.log_event(
            'login_attempt',
            f"OAuth login initiated for provider {sso_provider.name}",
            sso_provider=sso_provider,
            request=request
        )

        return redirect(auth_url)

    except SSOProvider.DoesNotExist:
        logger.error(f"SSO provider {provider_id} not found")
        return HttpResponseBadRequest("SSO provider not found")
    except Exception as e:
        logger.error(f"OAuth login error: {str(e)}")
        return HttpResponseBadRequest("OAuth login failed")


def oauth_callback(request, provider_id):
    """
    OAuth callback handler - process authorization code.
    """
    tenant = get_tenant_from_request(request)
    if not tenant:
        return HttpResponseBadRequest("Tenant not found")

    # Get authorization code and state
    code = request.GET.get('code') or request.POST.get('code')
    state = request.GET.get('state') or request.POST.get('state')
    error = request.GET.get('error') or request.POST.get('error')

    if error:
        logger.error(f"OAuth error: {error}")
        return render(request, 'sso/login_error.html', {
            'error': f'OAuth authentication failed: {error}'
        })

    if not code:
        return HttpResponseBadRequest("Authorization code not provided")

    # Verify state parameter
    expected_state = request.session.get('oauth_state')
    expected_provider_id = request.session.get('oauth_provider_id')

    if not expected_state or state != expected_state:
        logger.error("OAuth state mismatch - possible CSRF attack")
        return HttpResponseBadRequest("Invalid state parameter")

    if expected_provider_id != str(provider_id):
        logger.error("OAuth provider ID mismatch")
        return HttpResponseBadRequest("Invalid provider ID")

    # Clean up session
    if 'oauth_state' in request.session:
        del request.session['oauth_state']
    if 'oauth_provider_id' in request.session:
        del request.session['oauth_provider_id']

    try:
        # Authenticate user via OAuth backend
        from .oauth_backends import OAuthBackend
        backend = OAuthBackend()
        user = backend.authenticate(
            request,
            oauth_code=code,
            oauth_state=state,
            oauth_provider_id=provider_id
        )

        if user:
            # Log in the user
            login(request, user, backend='sso.oauth_backends.OAuthBackend')

            # Redirect to next URL or dashboard
            next_url = request.session.get('next_url', '/')
            if 'next_url' in request.session:
                del request.session['next_url']

            return redirect(next_url)
        else:
            # Authentication failed
            return render(request, 'sso/login_error.html', {
                'error': 'OAuth authentication failed'
            })

    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        return render(request, 'sso/login_error.html', {
            'error': 'An error occurred during authentication'
        })
