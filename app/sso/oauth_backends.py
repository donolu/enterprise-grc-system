"""
OAuth 2.0 / OpenID Connect authentication backend.
"""

import logging
import requests
import jwt
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from urllib.parse import urlencode

from .models import SSOProvider, OAuthProvider, SSOSession, SSOAuditLog
from .utils import get_tenant_from_request, provision_user_from_sso, get_mapped_attribute_value

User = get_user_model()
logger = logging.getLogger(__name__)


class OAuthBackend(BaseBackend):
    """
    OAuth 2.0 / OpenID Connect authentication backend.
    """

    def authenticate(self, request, oauth_code=None, oauth_state=None, oauth_provider_id=None):
        """
        Authenticate user via OAuth authorization code.
        """
        if not oauth_code or not oauth_provider_id:
            return None

        try:
            # Get tenant and SSO provider
            tenant = get_tenant_from_request(request)
            if not tenant:
                logger.error("No tenant found for OAuth authentication")
                return None

            sso_provider = SSOProvider.objects.get(
                id=oauth_provider_id,
                tenant=tenant,
                is_active=True,
                provider_type='oauth'
            )

            if not hasattr(sso_provider, 'oauth_config'):
                logger.error(f"OAuth config not found for provider {sso_provider.name}")
                return None

            oauth_config = sso_provider.oauth_config

            # Exchange authorization code for access token
            token_data = self._exchange_code_for_token(oauth_config, oauth_code, request)
            if not token_data:
                return None

            access_token = token_data.get('access_token')
            id_token = token_data.get('id_token')

            if not access_token:
                logger.error("No access token received from OAuth provider")
                return None

            # Get user information
            user_info = self._get_user_info(oauth_config, access_token, id_token)
            if not user_info:
                return None

            # Get or create user
            user = self._get_or_create_user(sso_provider, user_info, request)

            if user:
                # Create SSO session
                sso_session = SSOSession.objects.create(
                    user=user,
                    sso_provider=sso_provider,
                    sso_session_id=token_data.get('refresh_token', ''),
                    ip_address=SSOAuditLog.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    expires_at=self._calculate_token_expiry(token_data)
                )

                # Log successful authentication
                SSOAuditLog.log_event(
                    'login_success',
                    f"User {user.email} authenticated via OAuth",
                    sso_provider=sso_provider,
                    user=user,
                    request=request,
                    details={
                        'user_info': user_info,
                        'token_type': token_data.get('token_type', 'Bearer')
                    }
                )

                # Store SSO session in Django session
                request.session['sso_session_id'] = str(sso_session.id)

                return user

        except SSOProvider.DoesNotExist:
            logger.error(f"SSO provider {oauth_provider_id} not found")
        except Exception as e:
            logger.error(f"OAuth authentication error: {str(e)}")
            SSOAuditLog.log_event(
                'error',
                f"OAuth authentication error: {str(e)}",
                request=request,
                success=False,
                error_message=str(e)
            )

        return None

    def _exchange_code_for_token(self, oauth_config, code, request):
        """
        Exchange authorization code for access token.
        """
        try:
            # Build redirect URI
            redirect_uri = request.build_absolute_uri(
                f'/sso/oauth/callback/{oauth_config.sso_provider.id}/'
            )

            # Prepare token request
            token_data = {
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': redirect_uri,
                'client_id': oauth_config.client_id,
                'client_secret': oauth_config.client_secret
            }

            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }

            # Make token request
            response = requests.post(
                oauth_config.token_url,
                data=token_data,
                headers=headers,
                verify=oauth_config.verify_ssl,
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Token exchange failed: {response.status_code} {response.text}")
                return None

        except Exception as e:
            logger.error(f"Token exchange error: {str(e)}")
            return None

    def _get_user_info(self, oauth_config, access_token, id_token=None):
        """
        Get user information from OAuth provider.
        """
        try:
            # If using OpenID Connect, try to decode ID token first
            if oauth_config.use_oidc and id_token:
                try:
                    # For production, you should verify the JWT signature
                    # This is a simplified version for demonstration
                    decoded_token = jwt.decode(
                        id_token,
                        options={"verify_signature": False}  # DO NOT DO THIS IN PRODUCTION
                    )
                    return decoded_token
                except Exception as e:
                    logger.warning(f"Failed to decode ID token: {str(e)}")

            # Fall back to UserInfo endpoint
            if oauth_config.userinfo_url:
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/json'
                }

                response = requests.get(
                    oauth_config.userinfo_url,
                    headers=headers,
                    verify=oauth_config.verify_ssl,
                    timeout=30
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"UserInfo request failed: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Failed to get user info: {str(e)}")
            return None

    def _calculate_token_expiry(self, token_data):
        """
        Calculate token expiry time.
        """
        expires_in = token_data.get('expires_in')
        if expires_in:
            try:
                return timezone.now() + timezone.timedelta(seconds=int(expires_in))
            except (ValueError, TypeError):
                pass
        return None

    def _get_or_create_user(self, sso_provider, user_info, request):
        """
        Get existing user or create via JIT provisioning.
        """
        # Try to find existing user by email
        email = self._get_user_attribute(sso_provider, user_info, 'email')
        if not email:
            logger.error("No email found in OAuth user info")
            return None

        try:
            # Try to find existing user
            user = User.objects.get(email=email)

            # Update user attributes from OAuth
            self._update_user_from_oauth(user, sso_provider, user_info)
            return user

        except User.DoesNotExist:
            # Create new user via JIT provisioning
            if sso_provider.enable_jit_provisioning:
                return provision_user_from_sso(
                    sso_provider, user_info, email, request
                )
            else:
                logger.warning(f"JIT provisioning disabled for {email}")
                return None

    def _get_user_attribute(self, sso_provider, user_info, field_name):
        """
        Get user attribute from OAuth user info based on mapping.
        """
        return get_mapped_attribute_value(sso_provider, user_info, field_name)

    def _update_user_from_oauth(self, user, sso_provider, user_info):
        """
        Update user fields from OAuth user info.
        """
        try:
            updated = False

            # Update basic fields
            for field in ['first_name', 'last_name']:
                value = self._get_user_attribute(sso_provider, user_info, field)
                if value and getattr(user, field) != value:
                    setattr(user, field, value)
                    updated = True

            if updated:
                user.save()

        except Exception as e:
            logger.error(f"Failed to update user from OAuth info: {str(e)}")

    def get_user(self, user_id):
        """
        Get user by ID for Django auth system.
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class OAuthClient:
    """
    Helper class for OAuth operations.
    """

    @staticmethod
    def build_authorization_url(oauth_config, request, state=None):
        """
        Build OAuth authorization URL.
        """
        # Build redirect URI
        redirect_uri = request.build_absolute_uri(
            f'/sso/oauth/callback/{oauth_config.sso_provider.id}/'
        )

        params = {
            'response_type': 'code',
            'client_id': oauth_config.client_id,
            'redirect_uri': redirect_uri,
            'scope': oauth_config.scope,
        }

        if state:
            params['state'] = state

        # Add OIDC parameters if enabled
        if oauth_config.use_oidc:
            params['response_mode'] = 'form_post'

        return f"{oauth_config.authorization_url}?{urlencode(params)}"

    @staticmethod
    def discover_oidc_configuration(discovery_url):
        """
        Discover OpenID Connect configuration from discovery URL.
        """
        try:
            response = requests.get(discovery_url, timeout=30)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"OIDC discovery failed: {str(e)}")

        return None

    @staticmethod
    def populate_oauth_config_from_discovery(oauth_config, discovery_data):
        """
        Populate OAuth configuration from OIDC discovery data.
        """
        if 'authorization_endpoint' in discovery_data:
            oauth_config.authorization_url = discovery_data['authorization_endpoint']

        if 'token_endpoint' in discovery_data:
            oauth_config.token_url = discovery_data['token_endpoint']

        if 'userinfo_endpoint' in discovery_data:
            oauth_config.userinfo_url = discovery_data['userinfo_endpoint']

        if 'jwks_uri' in discovery_data:
            oauth_config.jwks_url = discovery_data['jwks_uri']