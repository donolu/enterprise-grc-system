# TOTP QR Code Generation Issue

**Issue ID:** ISSUE-0001  
**Severity:** Minor  
**Status:** Open  
**Created:** 2025-08-22  
**Component:** Authentication (2FA TOTP)  

## Summary

TOTP setup endpoint (`/api/auth/2fa/setup-totp/`) encounters Unicode encoding issues when attempting to return QR code data and manual keys for authenticator app setup.

## Description

When implementing the TOTP 2FA setup functionality, the endpoint fails with `UnicodeDecodeError` during JSON serialization. The error occurs in the DRF JSON renderer when trying to serialize the response containing:

1. Base64-encoded QR code image data
2. Base32-encoded manual key for authenticator apps

## Error Details

```
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xde in position 1: invalid continuation byte
```

**Error Location:** `rest_framework/utils/encoders.py:52` in `default` method

## Technical Analysis

The issue appears to be related to how `django-otp`'s `TOTPDevice.bin_key` binary data is being handled during JSON serialization. Even when converting to base32 encoding, the REST framework JSON encoder encounters binary data in the response.

## Current Workaround

The TOTP device creation works correctly - users can:
1. Create TOTP devices via `/api/auth/2fa/setup-totp/`
2. Confirm TOTP setup via `/api/auth/2fa/confirm-totp/`
3. Use TOTP codes for authentication in `/api/auth/2fa/verify/`

The core TOTP functionality is operational; only the QR code generation response has encoding issues.

## Reproduction Steps

1. Register and login as a user
2. Call `POST /api/auth/2fa/setup-totp/` with valid password
3. Observe `UnicodeDecodeError` in response

## Expected vs Actual Behavior

**Expected:**
```json
{
  "message": "Scan QR code with your authenticator app",
  "qr_code": "data:image/png;base64,...",
  "manual_key": "ABCD1234EFGH5678",
  "device_id": 1
}
```

**Actual:** `UnicodeDecodeError` exception

## Proposed Solutions

1. **Short-term:** Return setup URL and manual key separately
2. **Medium-term:** Investigate DRF custom serializer for binary data
3. **Long-term:** Consider frontend QR generation using returned setup URL

## Impact Assessment

- **Functionality Impact:** Low - TOTP authentication works
- **User Experience Impact:** Medium - Manual key entry required instead of QR scan
- **Security Impact:** None - Authentication security is maintained

## Related Components

- `authn/views.py:SetupTOTPView`
- `django-otp` library integration
- Django REST Framework JSON renderer

## Resolution Priority

**Priority:** Low - Core functionality operational, UX enhancement needed

## Additional Notes

This issue emerged during comprehensive 2FA implementation. Email and Push 2FA methods work correctly. The TOTP method's authentication flow is functional; only the setup convenience feature (QR code) needs resolution.