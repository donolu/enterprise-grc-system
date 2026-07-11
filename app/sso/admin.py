"""
Django admin configuration for SSO models.
"""

from django.contrib import admin
from django.urls import path, reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.html import format_html
from django.utils import timezone
from django import forms

from .models import (
    SSOProvider, SAMLProvider, OAuthProvider,
    AttributeMapping, SSOSession, SSOAuditLog
)
from .utils import generate_saml_metadata, validate_sso_configuration


class AttributeMappingInline(admin.TabularInline):
    model = AttributeMapping
    extra = 1
    fields = ['sso_attribute', 'user_field', 'is_required', 'default_value', 'transform_expression']


class SAMLProviderInline(admin.StackedInline):
    model = SAMLProvider
    fields = [
        'idp_sso_url', 'idp_sls_url', 'idp_x509_cert',
        'want_assertions_signed', 'want_name_id_encrypted',
        'authn_requests_signed', 'logout_requests_signed',
        'signature_algorithm', 'digest_algorithm',
        'sp_x509_cert', 'sp_private_key'
    ]
    readonly_fields = ['sp_entity_id', 'sp_acs_url', 'sp_sls_url']


class OAuthProviderInline(admin.StackedInline):
    model = OAuthProvider
    fields = [
        'authorization_url', 'token_url', 'userinfo_url', 'jwks_url', 'discovery_url',
        'client_id', 'client_secret', 'grant_type', 'scope',
        'use_oidc', 'verify_ssl'
    ]


class SSOProviderForm(forms.ModelForm):
    class Meta:
        model = SSOProvider
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()

        # Validate configuration
        if self.instance.pk:
            errors = validate_sso_configuration(self.instance)
            if errors:
                raise forms.ValidationError(f"Configuration errors: {'; '.join(errors)}")

        return cleaned_data


@admin.register(SSOProvider)
class SSOProviderAdmin(admin.ModelAdmin):
    form = SSOProviderForm
    list_display = [
        'name', 'tenant', 'provider_type', 'provider_name',
        'is_active', 'is_primary', 'enforce_sso', 'created_at'
    ]
    list_filter = [
        'provider_type', 'provider_name', 'is_active',
        'is_primary', 'enforce_sso', 'created_at'
    ]
    search_fields = ['name', 'tenant__name', 'entity_id']
    readonly_fields = ['id', 'created_at', 'updated_at']

    fieldsets = [
        ('Basic Configuration', {
            'fields': ['tenant', 'name', 'provider_type', 'provider_name']
        }),
        ('Status & Settings', {
            'fields': ['is_active', 'is_primary', 'enforce_sso']
        }),
        ('JIT Provisioning', {
            'fields': ['enable_jit_provisioning', 'jit_default_role']
        }),
        ('Advanced', {
            'fields': ['entity_id'],
            'classes': ['collapse']
        }),
        ('Metadata', {
            'fields': ['id', 'created_at', 'updated_at', 'created_by'],
            'classes': ['collapse']
        })
    ]

    inlines = [SAMLProviderInline, OAuthProviderInline, AttributeMappingInline]

    actions = ['activate_providers', 'deactivate_providers', 'test_configuration']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<uuid:provider_id>/metadata/',
                self.admin_site.admin_view(self.metadata_view),
                name='sso_ssoprovider_metadata'
            ),
            path(
                '<uuid:provider_id>/test/',
                self.admin_site.admin_view(self.test_view),
                name='sso_ssoprovider_test'
            )
        ]
        return custom_urls + urls

    def metadata_view(self, request, provider_id):
        """Generate and download SAML metadata."""
        try:
            provider = SSOProvider.objects.get(pk=provider_id)
            if provider.provider_type == 'saml':
                metadata_xml = generate_saml_metadata(provider)
                if metadata_xml:
                    response = HttpResponse(
                        metadata_xml,
                        content_type='application/xml'
                    )
                    response['Content-Disposition'] = f'attachment; filename="{provider.name}_metadata.xml"'
                    return response

            self.message_user(request, "Metadata generation failed", level='error')

        except SSOProvider.DoesNotExist:
            self.message_user(request, "Provider not found", level='error')

        return HttpResponseRedirect(reverse('admin:sso_ssoprovider_changelist'))

    def test_view(self, request, provider_id):
        """Test SSO provider configuration."""
        try:
            provider = SSOProvider.objects.get(pk=provider_id)
            errors = validate_sso_configuration(provider)

            if errors:
                self.message_user(
                    request,
                    f"Configuration errors found: {'; '.join(errors)}",
                    level='error'
                )
            else:
                self.message_user(
                    request,
                    "Configuration validation passed",
                    level='success'
                )

        except SSOProvider.DoesNotExist:
            self.message_user(request, "Provider not found", level='error')

        return HttpResponseRedirect(
            reverse('admin:sso_ssoprovider_change', args=[provider_id])
        )

    def activate_providers(self, request, queryset):
        """Bulk activate SSO providers."""
        queryset.update(is_active=True)
        self.message_user(request, f"Activated {queryset.count()} providers")
    activate_providers.short_description = "Activate selected providers"

    def deactivate_providers(self, request, queryset):
        """Bulk deactivate SSO providers."""
        queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {queryset.count()} providers")
    deactivate_providers.short_description = "Deactivate selected providers"

    def test_configuration(self, request, queryset):
        """Test configuration for selected providers."""
        results = []
        for provider in queryset:
            errors = validate_sso_configuration(provider)
            if errors:
                results.append(f"{provider.name}: {'; '.join(errors)}")

        if results:
            self.message_user(
                request,
                f"Configuration errors: {'; '.join(results)}",
                level='warning'
            )
        else:
            self.message_user(
                request,
                f"All {queryset.count()} configurations are valid",
                level='success'
            )
    test_configuration.short_description = "Test selected configurations"


@admin.register(AttributeMapping)
class AttributeMappingAdmin(admin.ModelAdmin):
    list_display = [
        'sso_provider', 'sso_attribute', 'user_field',
        'is_required', 'default_value'
    ]
    list_filter = ['user_field', 'is_required', 'sso_provider__provider_type']
    search_fields = ['sso_attribute', 'sso_provider__name']

    fieldsets = [
        (None, {
            'fields': ['sso_provider', 'sso_attribute', 'user_field']
        }),
        ('Configuration', {
            'fields': ['is_required', 'default_value', 'transform_expression']
        })
    ]


@admin.register(SSOSession)
class SSOSessionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'sso_provider', 'status', 'created_at',
        'last_accessed', 'expires_at', 'ip_address'
    ]
    list_filter = [
        'status', 'sso_provider', 'created_at', 'expires_at'
    ]
    search_fields = [
        'user__email', 'user__username',
        'sso_provider__name', 'ip_address'
    ]
    readonly_fields = [
        'id', 'created_at', 'last_accessed', 'sso_session_id', 'sso_name_id'
    ]
    date_hierarchy = 'created_at'

    fieldsets = [
        ('Session Info', {
            'fields': [
                'id', 'user', 'sso_provider', 'status',
                'sso_session_id', 'sso_name_id'
            ]
        }),
        ('Timing', {
            'fields': ['created_at', 'last_accessed', 'expires_at']
        }),
        ('Request Info', {
            'fields': ['ip_address', 'user_agent']
        })
    ]

    actions = ['terminate_sessions', 'cleanup_expired']

    def terminate_sessions(self, request, queryset):
        """Terminate selected sessions."""
        queryset.filter(status='active').update(
            status='terminated',
            last_accessed=timezone.now()
        )
        count = queryset.count()
        self.message_user(request, f"Terminated {count} sessions")
    terminate_sessions.short_description = "Terminate selected sessions"

    def cleanup_expired(self, request, queryset):
        """Mark expired sessions as expired."""
        now = timezone.now()
        expired = queryset.filter(
            status='active',
            expires_at__lt=now
        ).update(status='expired')

        self.message_user(request, f"Marked {expired} sessions as expired")
    cleanup_expired.short_description = "Cleanup expired sessions"


@admin.register(SSOAuditLog)
class SSOAuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'event_type', 'event_timestamp', 'sso_provider',
        'user', 'success', 'ip_address'
    ]
    list_filter = [
        'event_type', 'success', 'event_timestamp',
        'sso_provider__name'
    ]
    search_fields = [
        'message', 'user__email', 'sso_provider__name',
        'ip_address', 'request_id'
    ]
    readonly_fields = [
        'id', 'event_timestamp', 'details', 'ip_address',
        'user_agent', 'request_id'
    ]
    date_hierarchy = 'event_timestamp'

    fieldsets = [
        ('Event Details', {
            'fields': [
                'id', 'event_type', 'event_timestamp',
                'message', 'success'
            ]
        }),
        ('Related Objects', {
            'fields': ['sso_provider', 'user', 'sso_session']
        }),
        ('Request Context', {
            'fields': ['ip_address', 'user_agent', 'request_id'],
            'classes': ['collapse']
        }),
        ('Additional Data', {
            'fields': ['details', 'error_message'],
            'classes': ['collapse']
        })
    ]

    def has_add_permission(self, request):
        """Prevent manual creation of audit logs."""
        return False

    def has_change_permission(self, request, obj=None):
        """Prevent modification of audit logs."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup purposes."""
        return request.user.is_superuser


# Register inline admins
admin.site.register(SAMLProvider)
admin.site.register(OAuthProvider)