"""
Enhanced TOTP service using pyotp library for improved QR code generation.
This addresses the Unicode encoding issues with django-otp.
"""

import pyotp
import qrcode
import secrets
import base64
from io import BytesIO
from django.conf import settings
from django.contrib.auth import get_user_model
from django_otp.plugins.otp_totp.models import TOTPDevice
from typing import Dict, Optional, Tuple

User = get_user_model()


class TOTPService:
    """Enhanced TOTP service using pyotp for reliable QR code generation."""
    
    @staticmethod
    def generate_secret() -> str:
        """Generate a secure random secret for TOTP."""
        return pyotp.random_base32()
    
    @staticmethod
    def create_provisioning_uri(
        secret: str, 
        user_email: str, 
        issuer_name: str = None
    ) -> str:
        """
        Create a provisioning URI for TOTP setup.
        
        Args:
            secret: Base32 encoded secret
            user_email: User's email address
            issuer_name: Name of the service (defaults to site name)
        
        Returns:
            Provisioning URI for QR code generation
        """
        if not issuer_name:
            issuer_name = getattr(settings, 'SITE_NAME', 'GRC Platform')
        
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=user_email,
            issuer_name=issuer_name
        )
    
    @staticmethod
    def generate_qr_code(provisioning_uri: str) -> str:
        """
        Generate QR code image as base64 data URL.
        
        Args:
            provisioning_uri: TOTP provisioning URI
            
        Returns:
            Base64 encoded QR code image as data URL
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        # Create QR code image
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = BytesIO()
        qr_image.save(buffer, format='PNG')
        buffer.seek(0)
        
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{qr_base64}"
    
    @staticmethod
    def verify_token(secret: str, token: str, window: int = 1) -> bool:
        """
        Verify a TOTP token.
        
        Args:
            secret: Base32 encoded secret
            token: 6-digit TOTP token
            window: Time window for verification (default 1 = 30 seconds before/after)
            
        Returns:
            True if token is valid, False otherwise
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=window)
    
    @staticmethod
    def setup_totp_device(
        user: User, 
        password: str,
        device_name: str = None
    ) -> Dict[str, any]:
        """
        Set up a new TOTP device for a user.
        
        Args:
            user: User instance
            password: User's password for verification
            device_name: Optional device name
            
        Returns:
            Dictionary containing setup information
            
        Raises:
            ValueError: If password is incorrect or setup fails
        """
        # Verify password
        if not user.check_password(password):
            raise ValueError("Invalid password")
        
        # Remove any existing unconfirmed TOTP devices
        TOTPDevice.objects.filter(user=user, confirmed=False).delete()
        
        # Generate secret using pyotp
        secret = TOTPService.generate_secret()
        
        # Create provisioning URI
        provisioning_uri = TOTPService.create_provisioning_uri(
            secret=secret,
            user_email=user.email,
        )
        
        # Generate QR code
        qr_code_data_url = TOTPService.generate_qr_code(provisioning_uri)
        
        # Create django-otp device with the generated secret
        device = TOTPDevice.objects.create(
            user=user,
            name=device_name or f'Authenticator App - {user.username}',
            confirmed=False
        )
        
        # Set the secret on the device
        # We need to convert our base32 secret to the format django-otp expects
        device.key = secret
        device.save()
        
        return {
            'device_id': device.id,
            'secret': secret,
            'provisioning_uri': provisioning_uri,
            'qr_code': qr_code_data_url,
            'manual_entry_key': TOTPService.format_secret_for_manual_entry(secret)
        }
    
    @staticmethod
    def format_secret_for_manual_entry(secret: str) -> str:
        """
        Format secret for manual entry (groups of 4 characters).
        
        Args:
            secret: Base32 encoded secret
            
        Returns:
            Formatted secret for manual entry
        """
        # Group the secret into chunks of 4 for easier manual entry
        chunks = [secret[i:i+4] for i in range(0, len(secret), 4)]
        return ' '.join(chunks)
    
    @staticmethod
    def confirm_totp_setup(user: User, token: str) -> Tuple[bool, Optional[TOTPDevice]]:
        """
        Confirm TOTP setup by verifying a token.
        
        Args:
            user: User instance
            token: 6-digit TOTP token from authenticator app
            
        Returns:
            Tuple of (success: bool, device: TOTPDevice or None)
        """
        try:
            # Find unconfirmed TOTP device
            device = TOTPDevice.objects.get(user=user, confirmed=False)
        except TOTPDevice.DoesNotExist:
            return False, None
        
        # Verify token using pyotp
        if TOTPService.verify_token(device.key, token):
            device.confirmed = True
            device.save()
            return True, device
        
        return False, None
    
    @staticmethod
    def get_current_token(secret: str) -> str:
        """
        Get the current TOTP token for testing purposes.
        
        Args:
            secret: Base32 encoded secret
            
        Returns:
            Current 6-digit TOTP token
        """
        totp = pyotp.TOTP(secret)
        return totp.now()