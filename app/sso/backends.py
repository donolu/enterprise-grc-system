"""
Django authentication backends for SSO providers.
"""

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
import logging

from .models import SSOProvider, SAMLProvider, SSOSession, SSOAuditLog, AttributeMapping
from .utils import get_tenant_from_request, provision_user_from_sso

User = get_user_model()
logger = logging.getLogger(__name__)


def get_saml_auth_class():
    """Import the SAML client lazily so Django can start without loading xmlsec."""
    from onelogin.saml2.auth import OneLogin_Saml2_Auth

    return OneLogin_Saml2_Auth


class SAMLBackend(BaseBackend):
    """
    SAML 2.0 authentication backend.
    """

    def authenticate(self, request, saml_response=None, saml_provider_id=None):
        """
        Authenticate user via SAML response.
        """
        if not saml_response or not saml_provider_id:
            return None

        try:
            # Get tenant and SSO provider
            tenant = get_tenant_from_request(request)
            if not tenant:
                logger.error("No tenant found for SAML authentication")
                return None

            sso_provider = SSOProvider.objects.get(
                id=saml_provider_id,
                tenant=tenant,
                is_active=True,
                provider_type='saml'
            )

            if not hasattr(sso_provider, 'saml_config'):
                logger.error(f"SAML config not found for provider {sso_provider.name}")
                return None

            # Initialize SAML auth
            saml_auth = self._init_saml_auth(request, sso_provider.saml_config)
            if not saml_auth:
                return None

            # Process SAML response
            saml_auth.process_response()

            if not saml_auth.is_authenticated():
                errors = saml_auth.get_errors()
                logger.error(f"SAML authentication failed: {errors}")
                SSOAuditLog.log_event(
                    'login_failure',
                    f"SAML authentication failed: {', '.join(errors)}",
                    sso_provider=sso_provider,
                    request=request,
                    success=False,
                    error_message=str(errors)
                )
                return None

            # Extract user attributes
            attributes = saml_auth.get_attributes()
            name_id = saml_auth.get_nameid()
            session_index = saml_auth.get_session_index()

            # Get or create user
            user = self._get_or_create_user(
                sso_provider, attributes, name_id, request
            )

            if user:
                # Create SSO session
                sso_session = SSOSession.objects.create(
                    user=user,
                    sso_provider=sso_provider,
                    sso_session_id=session_index,
                    sso_name_id=name_id,
                    ip_address=SSOAuditLog.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )

                # Log successful authentication
                SSOAuditLog.log_event(
                    'login_success',
                    f"User {user.email} authenticated via SAML",
                    sso_provider=sso_provider,
                    user=user,
                    request=request,
                    details={
                        'name_id': name_id,
                        'session_index': session_index,
                        'attributes': attributes
                    }
                )

                # Store SSO session in Django session
                request.session['sso_session_id'] = str(sso_session.id)

                return user

        except SSOProvider.DoesNotExist:
            logger.error(f"SSO provider {saml_provider_id} not found")
        except Exception as e:
            logger.error(f"SAML authentication error: {str(e)}")
            SSOAuditLog.log_event(
                'error',
                f"SAML authentication error: {str(e)}",
                request=request,
                success=False,
                error_message=str(e)
            )

        return None

    def _init_saml_auth(self, request, saml_config):
        """
        Initialize SAML auth object with configuration.
        """
        try:
            # Prepare request data for OneLogin
            req = self._prepare_django_request(request)

            # Build SAML settings
            settings_data = {
                'sp': {
                    'entityId': saml_config.sp_entity_id,
                    'assertionConsumerService': {
                        'url': saml_config.sp_acs_url,
                        'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST'
                    },
                    'singleLogoutService': {
                        'url': saml_config.sp_sls_url,
                        'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
                    },
                    'NameIDFormat': 'urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress',
                    'x509cert': saml_config.sp_x509_cert,
                    'privateKey': saml_config.sp_private_key
                },
                'idp': {
                    'entityId': saml_config.sso_provider.entity_id,
                    'singleSignOnService': {
                        'url': saml_config.idp_sso_url,
                        'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
                    },
                    'singleLogoutService': {
                        'url': saml_config.idp_sls_url,
                        'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
                    },
                    'x509cert': saml_config.idp_x509_cert
                },
                'security': {
                    'nameIdEncrypted': saml_config.want_name_id_encrypted,
                    'authnRequestsSigned': saml_config.authn_requests_signed,
                    'logoutRequestSigned': saml_config.logout_requests_signed,
                    'wantAssertionsSigned': saml_config.want_assertions_signed,
                    'signatureAlgorithm': f'http://www.w3.org/2001/04/xmldsig-more#{saml_config.signature_algorithm.lower()}',
                    'digestAlgorithm': f'http://www.w3.org/2001/04/xmlenc#{saml_config.digest_algorithm.lower()}'
                }
            }

            saml_auth_class = get_saml_auth_class()
            return saml_auth_class(req, settings_data)

        except Exception as e:
            logger.error(f"Failed to initialize SAML auth: {str(e)}")
            return None

    def _prepare_django_request(self, request):
        """
        Convert Django request to OneLogin format.
        """
        return {
            'https': 'on' if request.is_secure() else 'off',
            'http_host': request.META['HTTP_HOST'],
            'server_port': request.META['SERVER_PORT'],
            'script_name': request.path,
            'get_data': request.GET.copy(),
            'post_data': request.POST.copy()
        }

    def _get_or_create_user(self, sso_provider, attributes, name_id, request):
        """
        Get existing user or create via JIT provisioning.
        """
        # Try to find existing user by email from attributes
        email = self._get_mapped_attribute(sso_provider, attributes, 'email')
        if not email:
            email = name_id  # Fallback to name_id

        if not email:
            logger.error("No email found in SAML attributes")
            return None

        try:
            # Try to find existing user
            user = User.objects.get(email=email)

            # Update user attributes from SSO
            self._update_user_from_attributes(user, sso_provider, attributes)
            return user

        except User.DoesNotExist:
            # Create new user via JIT provisioning
            if sso_provider.enable_jit_provisioning:
                return provision_user_from_sso(
                    sso_provider, attributes, name_id, request
                )
            else:
                logger.warning(f"JIT provisioning disabled for {email}")
                return None

    def _get_mapped_attribute(self, sso_provider, attributes, field_name):
        """
        Get attribute value based on mapping configuration.
        """
        try:
            mapping = AttributeMapping.objects.get(
                sso_provider=sso_provider,
                user_field=field_name
            )

            # Get attribute value
            sso_attr = mapping.sso_attribute
            value = attributes.get(sso_attr, [None])[0]

            if not value and mapping.default_value:
                value = mapping.default_value

            # Apply transformation if configured
            if mapping.transform_expression and value:
                try:
                    # Safe evaluation of transform expression
                    local_vars = {'value': value, 'attributes': attributes}
                    value = eval(mapping.transform_expression, {"__builtins__": {}}, local_vars)
                except Exception as e:
                    logger.error(f"Transform expression error: {str(e)}")

            return value

        except AttributeMapping.DoesNotExist:
            # Use default attribute names
            default_mappings = {
                'email': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress',
                'first_name': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname',
                'last_name': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname'
            }

            if field_name in default_mappings:
                attr_name = default_mappings[field_name]
                return attributes.get(attr_name, [None])[0]

        return None

    def _update_user_from_attributes(self, user, sso_provider, attributes):
        """
        Update user fields from SSO attributes.
        """
        try:
            updated = False

            # Update basic fields
            for field in ['first_name', 'last_name']:
                value = self._get_mapped_attribute(sso_provider, attributes, field)
                if value and getattr(user, field) != value:
                    setattr(user, field, value)
                    updated = True

            if updated:
                user.save()

        except Exception as e:
            logger.error(f"Failed to update user from attributes: {str(e)}")

    def get_user(self, user_id):
        """
        Get user by ID for Django auth system.
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
