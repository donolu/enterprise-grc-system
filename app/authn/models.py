from django.db import models
from django.contrib.auth import get_user_model
from django_otp.models import Device
import uuid
import json

User = get_user_model()

class PushDevice(Device):
    """
    A custom OTP device for push notifications.
    This device sends push notifications to mobile apps for authentication approval.
    """
    # Device registration token (FCM, APNs, etc.)
    device_token = models.TextField(help_text="Push notification device token")
    
    # Device metadata
    device_name = models.CharField(max_length=100, help_text="User-friendly device name")
    device_type = models.CharField(max_length=20, choices=[
        ('ios', 'iOS'),
        ('android', 'Android'),
        ('web', 'Web Browser')
    ])
    
    # Push service configuration
    push_service = models.CharField(max_length=20, choices=[
        ('fcm', 'Firebase Cloud Messaging'),
        ('apns', 'Apple Push Notification Service'),
        ('web_push', 'Web Push')
    ])
    
    # Authentication challenge storage
    pending_challenge = models.TextField(blank=True, help_text="JSON data for pending auth challenge")
    challenge_expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Push Device"
        
    def generate_challenge(self, extra_context=None):
        """
        Generate a push notification challenge.
        This creates a unique challenge ID and sends a push notification.
        """
        import time
        from datetime import datetime, timedelta
        
        challenge_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(minutes=5)  # 5 minute expiry
        
        challenge_data = {
            'challenge_id': challenge_id,
            'user_id': self.user.id,
            'username': self.user.username,
            'timestamp': int(time.time()),
            'expires_at': expires_at.isoformat(),
            'extra_context': extra_context or {}
        }
        
        self.pending_challenge = json.dumps(challenge_data)
        self.challenge_expires_at = expires_at
        self.save()
        
        # Send push notification (implement based on your push service)
        self._send_push_notification(challenge_data)
        
        return challenge_id
    
    def verify_token(self, token):
        """
        Verify a push notification approval.
        Token should be the challenge_id that was approved.
        """
        if not self.pending_challenge:
            return False
            
        try:
            challenge_data = json.loads(self.pending_challenge)
            
            # Check if token matches and hasn't expired
            if (challenge_data.get('challenge_id') == token and 
                self.challenge_expires_at and 
                self.challenge_expires_at > datetime.now()):
                
                # Clear the challenge
                self.pending_challenge = ''
                self.challenge_expires_at = None
                self.save()
                return True
                
        except (json.JSONDecodeError, KeyError):
            pass
            
        return False
    
    def _send_push_notification(self, challenge_data):
        """
        Send the actual push notification.
        This is a placeholder - implement based on your push service.
        """
        # Example implementation for FCM:
        if self.push_service == 'fcm':
            self._send_fcm_notification(challenge_data)
        elif self.push_service == 'apns':
            self._send_apns_notification(challenge_data)
        elif self.push_service == 'web_push':
            self._send_web_push_notification(challenge_data)
    
    def _send_fcm_notification(self, challenge_data):
        """Send FCM push notification"""
        # TODO: Implement FCM integration
        # Use Firebase Admin SDK or requests to FCM API
        pass
    
    def _send_apns_notification(self, challenge_data):
        """Send Apple Push notification"""
        # TODO: Implement APNs integration
        # Use PyAPNs or requests to APNs
        pass
    
    def _send_web_push_notification(self, challenge_data):
        """Send Web Push notification"""
        # TODO: Implement Web Push integration
        # Use py-vapid for web push
        pass

class UserDevicePreference(models.Model):
    """
    User preferences for 2FA methods and fallback order.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='auth_preferences')
    
    # Preferred 2FA method order
    primary_method = models.CharField(max_length=20, choices=[
        ('email', 'Email OTP'),
        ('totp', 'Authenticator App'),
        ('push', 'Push Notification')
    ], default='email')
    
    # Fallback methods
    fallback_methods = models.JSONField(default=list, help_text="Ordered list of fallback methods")
    
    # Security settings
    require_2fa_for_sensitive_actions = models.BooleanField(default=True)
    remember_device_days = models.PositiveIntegerField(default=30)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)