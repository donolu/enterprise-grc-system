"""
Single Sign-On Models

Enterprise SSO configuration and management for SAML and OAuth providers.
"""

import uuid
import json
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import URLValidator
from django.conf import settings
from core.models import Tenant

User = get_user_model()


class SSOProvider(models.Model):
    """
    SSO provider configuration for tenants.
    Supports SAML and OAuth/OIDC providers.
    """

    PROVIDER_TYPES = [
        ('saml', 'SAML 2.0'),
        ('oauth', 'OAuth 2.0 / OpenID Connect'),
    ]

    WELL_KNOWN_PROVIDERS = [
        ('custom', 'Custom Configuration'),
        ('okta', 'Okta'),
        ('azure_ad', 'Azure Active Directory'),
        ('google_workspace', 'Google Workspace'),
        ('microsoft_365', 'Microsoft 365'),
        ('aws_sso', 'AWS SSO'),
        ('onelogin', 'OneLogin'),
        ('auth0', 'Auth0'),
        ('ping_identity', 'Ping Identity'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='sso_providers')

    # Basic configuration
    name = models.CharField(max_length=100, help_text="Display name for this SSO provider")
    provider_type = models.CharField(max_length=10, choices=PROVIDER_TYPES)
    provider_name = models.CharField(
        max_length=50,
        choices=WELL_KNOWN_PROVIDERS,
        default='custom',
        help_text="Pre-configured provider or custom"
    )

    # Status and settings
    is_active = models.BooleanField(default=False)
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary SSO provider for this tenant"
    )
    enforce_sso = models.BooleanField(
        default=False,
        help_text="Disable password authentication when SSO is available"
    )

    # JIT provisioning
    enable_jit_provisioning = models.BooleanField(
        default=True,
        help_text="Automatically create user accounts from SSO"
    )
    jit_default_role = models.CharField(
        max_length=50,
        default='user',
        help_text="Default role for JIT-provisioned users"
    )

    # Common settings
    entity_id = models.CharField(max_length=500, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_sso_providers'
    )

    class Meta:
        unique_together = ['tenant', 'name']
        indexes = [
            models.Index(fields=['tenant', 'is_active']),
            models.Index(fields=['tenant', 'is_primary']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_provider_type_display()}) - {self.tenant.name}"

    def clean(self):
        """Validate SSO provider configuration."""
        from django.core.exceptions import ValidationError

        # Only one primary provider per tenant
        if self.is_primary:
            existing_primary = SSOProvider.objects.filter(
                tenant=self.tenant,
                is_primary=True
            ).exclude(id=self.id)

            if existing_primary.exists():
                raise ValidationError("Only one primary SSO provider allowed per tenant")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class SAMLProvider(models.Model):
    """
    SAML 2.0 specific configuration.
    """

    SIGNATURE_ALGORITHMS = [
        ('RSA_SHA256', 'RSA-SHA256'),
        ('RSA_SHA1', 'RSA-SHA1'),
        ('DSA_SHA1', 'DSA-SHA1'),
    ]

    DIGEST_ALGORITHMS = [
        ('SHA256', 'SHA256'),
        ('SHA1', 'SHA1'),
    ]

    sso_provider = models.OneToOneField(
        SSOProvider,
        on_delete=models.CASCADE,
        related_name='saml_config'
    )

    # Identity Provider settings
    idp_sso_url = models.URLField(help_text="IdP Single Sign-On URL")
    idp_sls_url = models.URLField(
        blank=True,
        help_text="IdP Single Logout Service URL (optional)"
    )
    idp_x509_cert = models.TextField(
        help_text="IdP X.509 Certificate (Base64 encoded)"
    )

    # Service Provider settings (auto-generated)
    sp_entity_id = models.CharField(max_length=500, blank=True)
    sp_acs_url = models.URLField(blank=True, help_text="Assertion Consumer Service URL")
    sp_sls_url = models.URLField(blank=True, help_text="Single Logout Service URL")

    # Security settings
    want_assertions_signed = models.BooleanField(default=True)
    want_name_id_encrypted = models.BooleanField(default=False)
    authn_requests_signed = models.BooleanField(default=False)
    logout_requests_signed = models.BooleanField(default=False)
    signature_algorithm = models.CharField(
        max_length=20,
        choices=SIGNATURE_ALGORITHMS,
        default='RSA_SHA256'
    )
    digest_algorithm = models.CharField(
        max_length=10,
        choices=DIGEST_ALGORITHMS,
        default='SHA256'
    )

    # Certificate for signing (optional)
    sp_x509_cert = models.TextField(
        blank=True,
        help_text="SP X.509 Certificate for signing (optional)"
    )
    sp_private_key = models.TextField(
        blank=True,
        help_text="SP Private Key for signing (optional)"
    )

    def __str__(self):
        return f"SAML Config for {self.sso_provider.name}"

    def generate_sp_urls(self):
        """Generate Service Provider URLs based on tenant domain."""
        tenant = self.sso_provider.tenant
        base_url = f"https://{tenant.get_primary_domain().domain}"

        if not self.sp_entity_id:
            self.sp_entity_id = f"{base_url}/saml/metadata/{self.sso_provider.id}/"

        if not self.sp_acs_url:
            self.sp_acs_url = f"{base_url}/saml/acs/{self.sso_provider.id}/"

        if not self.sp_sls_url:
            self.sp_sls_url = f"{base_url}/saml/sls/{self.sso_provider.id}/"


class OAuthProvider(models.Model):
    """
    OAuth 2.0 / OpenID Connect specific configuration.
    """

    GRANT_TYPES = [
        ('authorization_code', 'Authorization Code'),
        ('implicit', 'Implicit'),
        ('client_credentials', 'Client Credentials'),
    ]

    sso_provider = models.OneToOneField(
        SSOProvider,
        on_delete=models.CASCADE,
        related_name='oauth_config'
    )

    # OAuth/OIDC endpoints
    authorization_url = models.URLField(help_text="Authorization endpoint URL")
    token_url = models.URLField(help_text="Token endpoint URL")
    userinfo_url = models.URLField(
        blank=True,
        help_text="UserInfo endpoint URL (for OpenID Connect)"
    )
    jwks_url = models.URLField(
        blank=True,
        help_text="JSON Web Key Set URL (for OpenID Connect)"
    )
    discovery_url = models.URLField(
        blank=True,
        help_text="OpenID Connect Discovery URL (optional)"
    )

    # Client configuration
    client_id = models.CharField(max_length=255)
    client_secret = models.CharField(max_length=500)

    # OAuth settings
    grant_type = models.CharField(
        max_length=20,
        choices=GRANT_TYPES,
        default='authorization_code'
    )
    scope = models.CharField(
        max_length=500,
        default='openid profile email',
        help_text="Space-separated OAuth scopes"
    )

    # OpenID Connect settings
    use_oidc = models.BooleanField(
        default=True,
        help_text="Use OpenID Connect features"
    )
    verify_ssl = models.BooleanField(default=True)

    def __str__(self):
        return f"OAuth Config for {self.sso_provider.name}"


class AttributeMapping(models.Model):
    """
    Maps SSO provider attributes to user fields.
    """

    USER_FIELDS = [
        ('email', 'Email'),
        ('first_name', 'First Name'),
        ('last_name', 'Last Name'),
        ('username', 'Username'),
        ('is_staff', 'Staff Status'),
        ('is_superuser', 'Superuser Status'),
        ('groups', 'Groups'),
    ]

    sso_provider = models.ForeignKey(
        SSOProvider,
        on_delete=models.CASCADE,
        related_name='attribute_mappings'
    )

    # Mapping configuration
    sso_attribute = models.CharField(
        max_length=100,
        help_text="Attribute name from SSO provider"
    )
    user_field = models.CharField(
        max_length=50,
        choices=USER_FIELDS,
        help_text="User model field to map to"
    )

    # Transformation settings
    is_required = models.BooleanField(default=False)
    default_value = models.CharField(
        max_length=255,
        blank=True,
        help_text="Default value if attribute not provided"
    )
    transform_expression = models.TextField(
        blank=True,
        help_text="Python expression to transform attribute value"
    )

    class Meta:
        unique_together = ['sso_provider', 'sso_attribute']

    def __str__(self):
        return f"{self.sso_attribute} → {self.user_field}"


class SSOSession(models.Model):
    """
    Tracks SSO authentication sessions for audit and management.
    """

    SESSION_STATUS = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('logged_out', 'Logged Out'),
        ('terminated', 'Terminated'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Session details
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sso_sessions')
    sso_provider = models.ForeignKey(SSOProvider, on_delete=models.CASCADE)

    # SSO session tracking
    sso_session_id = models.CharField(max_length=255, blank=True)
    sso_name_id = models.CharField(max_length=255, blank=True)

    # Session lifecycle
    created_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=SESSION_STATUS, default='active')

    # Audit information
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['sso_provider', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"SSO Session for {self.user.email} via {self.sso_provider.name}"

    def is_expired(self):
        """Check if session is expired."""
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return self.status in ['expired', 'logged_out', 'terminated']


class SSOAuditLog(models.Model):
    """
    Comprehensive audit logging for SSO events.
    """

    EVENT_TYPES = [
        ('login_attempt', 'Login Attempt'),
        ('login_success', 'Login Success'),
        ('login_failure', 'Login Failure'),
        ('logout', 'Logout'),
        ('jit_provisioning', 'JIT User Provisioning'),
        ('attribute_mapping', 'Attribute Mapping'),
        ('session_timeout', 'Session Timeout'),
        ('configuration_change', 'Configuration Change'),
        ('error', 'Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Event details
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    event_timestamp = models.DateTimeField(auto_now_add=True)

    # Related objects
    sso_provider = models.ForeignKey(
        SSOProvider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    sso_session = models.ForeignKey(
        SSOSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Event data
    message = models.TextField()
    details = models.JSONField(default=dict, blank=True)

    # Request context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_id = models.CharField(max_length=50, blank=True)

    # Status
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['event_timestamp']),
            models.Index(fields=['sso_provider', 'event_type']),
            models.Index(fields=['user', 'event_type']),
            models.Index(fields=['success', 'event_timestamp']),
        ]
        ordering = ['-event_timestamp']

    def __str__(self):
        return f"{self.get_event_type_display()} - {self.event_timestamp}"

    @classmethod
    def log_event(cls, event_type, message, sso_provider=None, user=None,
                  request=None, details=None, success=True, error_message=''):
        """Helper method to create audit log entries."""

        # Extract request context
        ip_address = None
        user_agent = ''
        request_id = ''

        if request:
            ip_address = cls.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            request_id = getattr(request, 'request_id', '')

        return cls.objects.create(
            event_type=event_type,
            message=message,
            sso_provider=sso_provider,
            user=user,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            success=success,
            error_message=error_message
        )

    @staticmethod
    def get_client_ip(request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip