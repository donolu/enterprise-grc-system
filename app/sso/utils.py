"""
SSO utility functions.
"""

import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.contrib.auth.models import Group
from django.utils import timezone
from django_tenants.utils import tenant_context

from .models import SSOProvider, SSOAuditLog, AttributeMapping

User = get_user_model()
logger = logging.getLogger(__name__)


def get_tenant_from_request(request):
    """
    Extract tenant from request.
    """
    return getattr(request, 'tenant', None)


def provision_user_from_sso(sso_provider, attributes, name_id, request):
    """
    Create a new user from SSO attributes via JIT provisioning.
    """
    try:
        with transaction.atomic():
            # Extract user data from attributes
            email = get_mapped_attribute_value(sso_provider, attributes, 'email')
            if not email:
                email = name_id

            if not email:
                logger.error("Cannot provision user without email")
                return None

            first_name = get_mapped_attribute_value(sso_provider, attributes, 'first_name') or ''
            last_name = get_mapped_attribute_value(sso_provider, attributes, 'last_name') or ''
            username = get_mapped_attribute_value(sso_provider, attributes, 'username') or email

            # Ensure unique username
            original_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{original_username}_{counter}"
                counter += 1

            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name
            )

            # Apply role mappings
            apply_role_mappings(user, sso_provider, attributes)

            # Set default role if no roles were mapped
            if not user.groups.exists() and sso_provider.jit_default_role:
                try:
                    default_group = Group.objects.get(name=sso_provider.jit_default_role)
                    user.groups.add(default_group)
                except Group.DoesNotExist:
                    logger.warning(f"Default role '{sso_provider.jit_default_role}' not found")

            # Apply staff/superuser status if mapped
            is_staff = get_mapped_attribute_value(sso_provider, attributes, 'is_staff')
            if is_staff is not None:
                user.is_staff = _convert_to_boolean(is_staff)

            is_superuser = get_mapped_attribute_value(sso_provider, attributes, 'is_superuser')
            if is_superuser is not None:
                user.is_superuser = _convert_to_boolean(is_superuser)

            user.save()

            # Log JIT provisioning
            SSOAuditLog.log_event(
                'jit_provisioning',
                f"User {email} provisioned via JIT from {sso_provider.name}",
                sso_provider=sso_provider,
                user=user,
                request=request,
                details={
                    'attributes': attributes,
                    'name_id': name_id,
                    'username': username,
                    'default_role': sso_provider.jit_default_role,
                    'groups': list(user.groups.values_list('name', flat=True))
                }
            )

            return user

    except Exception as e:
        logger.error(f"JIT provisioning failed: {str(e)}")
        SSOAuditLog.log_event(
            'error',
            f"JIT provisioning failed: {str(e)}",
            sso_provider=sso_provider,
            request=request,
            success=False,
            error_message=str(e)
        )
        return None


def apply_role_mappings(user, sso_provider, attributes):
    """
    Apply group/role mappings from SSO attributes.
    """
    try:
        # Get groups attribute value
        groups_value = get_mapped_attribute_value(sso_provider, attributes, 'groups')
        if not groups_value:
            return

        # Handle different group formats
        group_names = []
        if isinstance(groups_value, str):
            # Handle comma-separated string
            group_names = [name.strip() for name in groups_value.split(',')]
        elif isinstance(groups_value, list):
            # Handle list of group names
            group_names = groups_value

        # Map SSO groups to Django groups
        for group_name in group_names:
            if not group_name:
                continue

            # Apply group name transformations if needed
            django_group_name = transform_group_name(group_name)

            try:
                group = Group.objects.get(name=django_group_name)
                user.groups.add(group)
                logger.info(f"Added user {user.email} to group {django_group_name}")
            except Group.DoesNotExist:
                # Optionally create group automatically
                if getattr(settings, 'SSO_AUTO_CREATE_GROUPS', False):
                    group = Group.objects.create(name=django_group_name)
                    user.groups.add(group)
                    logger.info(f"Created and added user {user.email} to group {django_group_name}")
                else:
                    logger.warning(f"Group '{django_group_name}' not found for user {user.email}")

    except Exception as e:
        logger.error(f"Failed to apply role mappings: {str(e)}")


def transform_group_name(sso_group_name):
    """
    Transform SSO group names to Django group names.
    Customize this function based on your naming conventions.
    """
    # Example transformations:
    # - Convert to lowercase
    # - Replace spaces with underscores
    # - Remove domain prefixes

    name = sso_group_name.lower()
    name = name.replace(' ', '_')
    name = name.replace('-', '_')

    # Remove common prefixes
    prefixes_to_remove = ['domain\\', 'company_', 'org_']
    for prefix in prefixes_to_remove:
        if name.startswith(prefix):
            name = name[len(prefix):]

    return name


def _convert_to_boolean(value):
    """
    Convert various representations to boolean.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'on')
    return bool(value)


def get_mapped_attribute_value(sso_provider, attributes, field_name):
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
        values = attributes.get(sso_attr, [])
        value = values[0] if values else None

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
        # Use default attribute names for common fields
        default_mappings = {
            'email': ['http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress', 'email', 'mail'],
            'first_name': ['http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname', 'firstName', 'given_name'],
            'last_name': ['http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname', 'lastName', 'family_name'],
            'username': ['http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name', 'username', 'preferred_username']
        }

        if field_name in default_mappings:
            for attr_name in default_mappings[field_name]:
                values = attributes.get(attr_name, [])
                if values:
                    return values[0]

    return None


def generate_saml_metadata(sso_provider):
    """
    Generate SAML metadata XML for service provider.
    """
    if not hasattr(sso_provider, 'saml_config'):
        return None

    saml_config = sso_provider.saml_config

    # Ensure SP URLs are generated
    if not saml_config.sp_entity_id:
        saml_config.generate_sp_urls()
        saml_config.save()

    metadata_template = '''<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
                     xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
                     entityID="{entity_id}">
    <md:SPSSODescriptor
        AuthnRequestsSigned="{authn_requests_signed}"
        WantAssertionsSigned="{want_assertions_signed}"
        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">

        {certificate_section}

        <md:SingleLogoutService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            Location="{sls_url}"/>

        <md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</md:NameIDFormat>

        <md:AssertionConsumerService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            Location="{acs_url}"
            index="1"
            isDefault="true"/>

    </md:SPSSODescriptor>
</md:EntityDescriptor>'''

    # Include certificate if available
    certificate_section = ""
    if saml_config.sp_x509_cert:
        certificate_section = f'''<md:KeyDescriptor use="signing">
            <ds:KeyInfo>
                <ds:X509Data>
                    <ds:X509Certificate>{saml_config.sp_x509_cert.strip()}</ds:X509Certificate>
                </ds:X509Data>
            </ds:KeyInfo>
        </md:KeyDescriptor>'''

    return metadata_template.format(
        entity_id=saml_config.sp_entity_id,
        authn_requests_signed='true' if saml_config.authn_requests_signed else 'false',
        want_assertions_signed='true' if saml_config.want_assertions_signed else 'false',
        certificate_section=certificate_section,
        sls_url=saml_config.sp_sls_url,
        acs_url=saml_config.sp_acs_url
    )


def create_default_attribute_mappings(sso_provider):
    """
    Create default attribute mappings for new SSO providers.
    """
    default_mappings = [
        {
            'sso_attribute': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress',
            'user_field': 'email',
            'is_required': True
        },
        {
            'sso_attribute': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname',
            'user_field': 'first_name',
            'is_required': False
        },
        {
            'sso_attribute': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname',
            'user_field': 'last_name',
            'is_required': False
        }
    ]

    for mapping_data in default_mappings:
        AttributeMapping.objects.get_or_create(
            sso_provider=sso_provider,
            sso_attribute=mapping_data['sso_attribute'],
            defaults={
                'user_field': mapping_data['user_field'],
                'is_required': mapping_data['is_required']
            }
        )


def validate_sso_configuration(sso_provider):
    """
    Validate SSO provider configuration.
    """
    errors = []

    if sso_provider.provider_type == 'saml':
        if not hasattr(sso_provider, 'saml_config'):
            errors.append("SAML configuration is required")
        else:
            saml_config = sso_provider.saml_config

            if not saml_config.idp_sso_url:
                errors.append("Identity Provider SSO URL is required")

            if not saml_config.idp_x509_cert:
                errors.append("Identity Provider X.509 certificate is required")

    elif sso_provider.provider_type == 'oauth':
        if not hasattr(sso_provider, 'oauth_config'):
            errors.append("OAuth configuration is required")
        else:
            oauth_config = sso_provider.oauth_config

            if not oauth_config.client_id:
                errors.append("OAuth Client ID is required")

            if not oauth_config.client_secret:
                errors.append("OAuth Client Secret is required")

            if not oauth_config.authorization_url:
                errors.append("Authorization URL is required")

            if not oauth_config.token_url:
                errors.append("Token URL is required")

    # Check required attribute mappings
    if sso_provider.enable_jit_provisioning:
        try:
            email_mapping = AttributeMapping.objects.get(
                sso_provider=sso_provider,
                user_field='email'
            )
        except AttributeMapping.DoesNotExist:
            errors.append("Email attribute mapping is required for JIT provisioning")

    return errors


def cleanup_expired_sso_sessions():
    """
    Cleanup expired SSO sessions.
    """
    from .models import SSOSession

    expired_sessions = SSOSession.objects.filter(
        status='active',
        expires_at__lt=timezone.now()
    )

    count = expired_sessions.count()
    expired_sessions.update(status='expired')

    logger.info(f"Cleaned up {count} expired SSO sessions")
    return count
