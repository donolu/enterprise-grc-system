from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django_otp.plugins.otp_email.models import EmailDevice
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp import user_has_device
import qrcode
from io import BytesIO
import base64
import pyotp
import secrets
from .models import PushDevice, UserDevicePreference

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password', 'password_confirm')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        
        # Validate password strength
        try:
            validate_password(attrs['password'])
        except ValidationError as e:
            raise serializers.ValidationError({'password': e.messages})
        
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        
        user = User.objects.create_user(**validated_data)
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'})

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(request=self.context.get('request'),
                              username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include username and password')

class UserProfileSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'date_joined')
        read_only_fields = ('id', 'username', 'date_joined')

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(style={'input_type': 'password'})
    new_password = serializers.CharField(style={'input_type': 'password'})
    new_password_confirm = serializers.CharField(style={'input_type': 'password'})

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match")
        
        # Validate password strength
        try:
            validate_password(attrs['new_password'])
        except ValidationError as e:
            raise serializers.ValidationError({'new_password': e.messages})
        
        return attrs

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect')
        return value

class TwoFactorStatusSerializer(serializers.Serializer):
    email_enabled = serializers.BooleanField(read_only=True)
    totp_enabled = serializers.BooleanField(read_only=True)
    push_enabled = serializers.BooleanField(read_only=True)
    email = serializers.EmailField(read_only=True, required=False)
    push_devices = serializers.ListField(read_only=True, required=False)
    primary_method = serializers.CharField(read_only=True, required=False)

class EnableTwoFactorSerializer(serializers.Serializer):
    password = serializers.CharField(style={'input_type': 'password'})
    method = serializers.ChoiceField(choices=['email', 'totp', 'push'])
    email = serializers.EmailField(required=False)
    # For push notifications
    device_token = serializers.CharField(required=False)
    device_name = serializers.CharField(required=False)
    device_type = serializers.ChoiceField(choices=['ios', 'android', 'web'], required=False)
    push_service = serializers.ChoiceField(choices=['fcm', 'apns', 'web_push'], required=False)

    def validate_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Password is incorrect')
        return value

    def validate_email(self, value):
        # If no email provided, use user's email
        if not value:
            return self.context['request'].user.email
        return value

    def validate(self, attrs):
        method = attrs['method']
        
        if method == 'email' and not attrs.get('email'):
            attrs['email'] = self.context['request'].user.email
        elif method == 'push':
            required_fields = ['device_token', 'device_name', 'device_type', 'push_service']
            for field in required_fields:
                if not attrs.get(field):
                    raise serializers.ValidationError(f'{field} is required for push notifications')
        
        return attrs

class DisableTwoFactorSerializer(serializers.Serializer):
    password = serializers.CharField(style={'input_type': 'password'})
    method = serializers.ChoiceField(choices=['email', 'totp', 'push', 'all'], default='all')

    def validate_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Password is incorrect')
        return value

class VerifyOTPSerializer(serializers.Serializer):
    username = serializers.CharField()
    otp_code = serializers.CharField(max_length=6, min_length=6)

    def validate(self, attrs):
        username = attrs.get('username')
        otp_code = attrs.get('otp_code')

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError('Invalid user')

        # Try to verify with email device first
        try:
            email_device = EmailDevice.objects.get(user=user, confirmed=True)
            if email_device.verify_token(otp_code):
                attrs['user'] = user
                attrs['device'] = email_device
                return attrs
        except EmailDevice.DoesNotExist:
            pass

        # Try to verify with TOTP device
        try:
            totp_device = TOTPDevice.objects.get(user=user, confirmed=True)
            if totp_device.verify_token(otp_code):
                attrs['user'] = user
                attrs['device'] = totp_device
                return attrs
        except TOTPDevice.DoesNotExist:
            pass

        # Try to verify with Push device (challenge ID)
        try:
            push_device = PushDevice.objects.get(user=user, confirmed=True)
            if push_device.verify_token(otp_code):
                attrs['user'] = user
                attrs['device'] = push_device
                return attrs
        except PushDevice.DoesNotExist:
            pass

        raise serializers.ValidationError('Invalid or expired OTP code')

class SetupTOTPSerializer(serializers.Serializer):
    password = serializers.CharField(style={'input_type': 'password'})

    def validate_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Password is incorrect')
        return value

class ConfirmTOTPSerializer(serializers.Serializer):
    otp_code = serializers.CharField(max_length=6, min_length=6)

    def validate_otp_code(self, value):
        # This will be validated in the view with the device
        return value

class RegisterPushDeviceSerializer(serializers.Serializer):
    device_token = serializers.CharField()
    device_name = serializers.CharField(max_length=100)
    device_type = serializers.ChoiceField(choices=['ios', 'android', 'web'])
    push_service = serializers.ChoiceField(choices=['fcm', 'apns', 'web_push'])

class ApprovePushChallengeSerializer(serializers.Serializer):
    challenge_id = serializers.CharField()
    approved = serializers.BooleanField()

class UserPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDevicePreference
        fields = ['primary_method', 'fallback_methods', 'require_2fa_for_sensitive_actions', 'remember_device_days']