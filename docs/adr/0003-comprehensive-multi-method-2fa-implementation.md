# ADR-0003: Comprehensive Multi-Method Two-Factor Authentication Implementation

**Status:** Accepted  
**Date:** 2025-08-22  
**Deciders:** Development Team  

## Context

The application requires robust Two-Factor Authentication (2FA) to provide enterprise-grade security for sensitive GRC (Governance, Risk, and Compliance) data. The initial requirement was for basic email-based 2FA, but this was expanded to include multiple authentication methods to meet modern security expectations and enterprise requirements.

## Decision

We implemented a comprehensive multi-method 2FA system using `django-otp` as the foundation, enhanced with custom models and business logic to support:

1. **Email OTP** - Traditional email-based one-time passwords
2. **TOTP (Time-based OTP)** - Authenticator app support (Google Authenticator, Authy, Microsoft Authenticator)
3. **Push Notifications** - Mobile app-based push approvals

## Architecture

### Core Components

1. **django-otp Integration**
   - Leveraged `EmailDevice` and `TOTPDevice` from django-otp plugins
   - Configured as tenant-specific apps for multi-tenant isolation
   - Integrated with existing authentication flow

2. **Custom PushDevice Model**
   ```python
   class PushDevice(Device):
       device_token = models.TextField()  # FCM/APNs token
       device_name = models.CharField(max_length=100)
       device_type = models.CharField(choices=['ios', 'android', 'web'])
       push_service = models.CharField(choices=['fcm', 'apns', 'web_push'])
       pending_challenge = models.TextField(blank=True)
       challenge_expires_at = models.DateTimeField(null=True, blank=True)
   ```

3. **User Preferences System**
   ```python
   class UserDevicePreference(models.Model):
       user = models.OneToOneField(User, on_delete=models.CASCADE)
       primary_method = models.CharField(choices=['email', 'totp', 'push'])
       fallback_methods = models.JSONField(default=list)
       require_2fa_for_sensitive_actions = models.BooleanField(default=True)
       remember_device_days = models.PositiveIntegerField(default=30)
   ```

### API Endpoints

We implemented 10+ RESTful endpoints for complete 2FA lifecycle management:

- **Status & Management**: `/api/auth/2fa/status/`, `/api/auth/2fa/preferences/`
- **Enable/Disable**: `/api/auth/2fa/enable/`, `/api/auth/2fa/disable/`
- **Verification**: `/api/auth/2fa/verify/`
- **TOTP Setup**: `/api/auth/2fa/setup-totp/`, `/api/auth/2fa/confirm-totp/`
- **Push Management**: `/api/auth/2fa/register-push/`, `/api/auth/2fa/approve-push/`

### Authentication Flow

1. User enters username/password
2. System checks if user has confirmed 2FA devices
3. If 2FA enabled:
   - Retrieve user preferences for method priority
   - Attempt primary method (push → email → TOTP)
   - Generate challenge for applicable methods
   - Return challenge information to client
4. User provides 2FA token/approval
5. System verifies across all enabled methods
6. Complete authentication on successful verification

## Rationale

### Why Multi-Method Support?

1. **User Experience**: Different users prefer different authentication methods
2. **Enterprise Requirements**: Organizations often require specific 2FA methods for compliance
3. **Redundancy**: Multiple methods provide fallback options if one method fails
4. **Modern Security**: Follows current industry best practices for MFA

### Why django-otp?

1. **Django Integration**: Native Django app with excellent ORM integration
2. **Proven Security**: Well-established library with security audit history
3. **Extensibility**: Pluggable device system allows custom implementations
4. **Standards Compliance**: Implements HOTP/TOTP standards correctly

### Why Custom PushDevice?

1. **Mobile-First Security**: Push notifications provide better UX than codes
2. **Enterprise Features**: Challenge expiration, device management, audit trails
3. **Flexibility**: Supports multiple push services (FCM, APNs, Web Push)
4. **Integration Ready**: Prepared for future mobile app development

## Implementation Details

### Multi-Tenant Integration

- OTP models configured in `TENANT_APPS` for schema isolation
- All 2FA devices and preferences are tenant-specific
- No cross-tenant access possible

### Security Features

- Challenge expiration (5 minutes for push notifications)
- Secure token generation using cryptographically secure random
- Device confirmation requirements
- Audit trail through django-otp's built-in logging

### Error Handling

- Graceful fallback between methods
- Clear error messages for debugging
- Proper HTTP status codes for API consumers

## Consequences

### Positive

1. **Enhanced Security**: Multiple authentication factors significantly improve security posture
2. **User Choice**: Users can select their preferred authentication method
3. **Enterprise Ready**: Meets enterprise security requirements out of the box
4. **Scalable**: Architecture supports additional methods (SMS, hardware tokens, etc.)
5. **Standards Compliant**: Uses industry-standard TOTP/HOTP implementations

### Negative

1. **Complexity**: More complex than single-method 2FA
2. **Dependencies**: Additional dependency on `qrcode` library for TOTP setup
3. **Push Infrastructure**: Push notifications require additional infrastructure setup

### Neutral

1. **Learning Curve**: Users need to understand multiple authentication options
2. **Configuration**: Administrators need to understand preference system

## Future Considerations

1. **SMS Support**: Could be added as another device type
2. **Hardware Tokens**: U2F/WebAuthn support possible with additional devices
3. **Risk-Based Authentication**: Could integrate with user behavior analysis
4. **SSO Integration**: Could work alongside SAML/OAuth implementations

## Related Decisions

- [ADR-0002: User-Tenant Relationship via Schema Isolation](0002-user-tenant-relationship-via-schema-isolation.md)
- Future: ADR for push notification infrastructure setup

## References

- [django-otp Documentation](https://django-otp.readthedocs.io/)
- [RFC 6238: TOTP Algorithm](https://tools.ietf.org/html/rfc6238)
- [RFC 4226: HOTP Algorithm](https://tools.ietf.org/html/rfc4226)
- [NIST SP 800-63B: Authentication and Lifecycle Management](https://pages.nist.gov/800-63-3/)