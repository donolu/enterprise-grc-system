from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import login, logout
from django.contrib.auth import get_user_model
from django_otp.plugins.otp_email.models import EmailDevice
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp import user_has_device
import qrcode
from io import BytesIO
import base64
from django.conf import settings
from .models import PushDevice, UserDevicePreference
from .serializers import (
    RegisterSerializer, 
    LoginSerializer, 
    UserProfileSerializer,
    ChangePasswordSerializer,
    TwoFactorStatusSerializer,
    EnableTwoFactorSerializer,
    DisableTwoFactorSerializer,
    VerifyOTPSerializer,
    SetupTOTPSerializer,
    ConfirmTOTPSerializer,
    RegisterPushDeviceSerializer,
    ApprovePushChallengeSerializer,
    UserPreferencesSerializer
)

User = get_user_model()

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': 'User created successfully',
                'user_id': user.id
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Check if user has 2FA enabled
            if user_has_device(user, confirmed=True):
                # Get user preferences for 2FA method priority
                try:
                    preferences = UserDevicePreference.objects.get(user=user)
                    primary_method = preferences.primary_method
                except UserDevicePreference.DoesNotExist:
                    primary_method = 'email'  # Default to email
                
                # Try primary method first, then fallbacks
                method_used = None
                
                # Try primary method
                if primary_method == 'push':
                    try:
                        device = PushDevice.objects.get(user=user, confirmed=True)
                        challenge_id = device.generate_challenge()
                        method_used = 'push'
                        message = f'Push notification sent to your {device.device_name}'
                    except PushDevice.DoesNotExist:
                        pass
                
                if not method_used and (primary_method == 'totp' or primary_method == 'email'):
                    try:
                        device = EmailDevice.objects.get(user=user, confirmed=True)
                        device.generate_challenge()
                        method_used = 'email'
                        message = '2FA code sent to your email'
                    except EmailDevice.DoesNotExist:
                        pass
                
                # TOTP doesn't need challenge generation
                if not method_used:
                    try:
                        TOTPDevice.objects.get(user=user, confirmed=True)
                        method_used = 'totp'
                        message = 'Enter code from your authenticator app'
                    except TOTPDevice.DoesNotExist:
                        pass
                
                if method_used:
                    return Response({
                        'message': message,
                        'requires_2fa': True,
                        'username': user.username,
                        'method': method_used
                    }, status=status.HTTP_200_OK)
            
            # No 2FA or device not found, login normally
            login(request, user)
            profile_serializer = UserProfileSerializer(user)
            return Response({
                'message': 'Login successful',
                'user': profile_serializer.data,
                'requires_2fa': False
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        logout(request)
        return Response({
            'message': 'Logout successful'
        }, status=status.HTTP_200_OK)

class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    
    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({
                'message': 'Password changed successfully'
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def me(request):
    """Get current user info"""
    serializer = UserProfileSerializer(request.user)
    return Response(serializer.data)

class TwoFactorStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get comprehensive 2FA status for current user"""
        user = request.user
        
        # Check each 2FA method
        email_enabled = EmailDevice.objects.filter(user=user, confirmed=True).exists()
        totp_enabled = TOTPDevice.objects.filter(user=user, confirmed=True).exists()
        push_enabled = PushDevice.objects.filter(user=user, confirmed=True).exists()
        
        # Get push devices info
        push_devices = []
        if push_enabled:
            devices = PushDevice.objects.filter(user=user, confirmed=True)
            push_devices = [
                {
                    'id': device.id,
                    'name': device.device_name,
                    'type': device.device_type,
                    'service': device.push_service
                }
                for device in devices
            ]
        
        # Get user preferences
        try:
            preferences = UserDevicePreference.objects.get(user=user)
            primary_method = preferences.primary_method
        except UserDevicePreference.DoesNotExist:
            primary_method = 'email'
        
        data = {
            'email_enabled': email_enabled,
            'totp_enabled': totp_enabled,
            'push_enabled': push_enabled,
            'email': user.email,
            'push_devices': push_devices,
            'primary_method': primary_method
        }
        
        serializer = TwoFactorStatusSerializer(data)
        return Response(serializer.data)

class EnableTwoFactorView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Enable 2FA for current user - supports email, TOTP, and push"""
        serializer = EnableTwoFactorSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            method = serializer.validated_data['method']
            
            if method == 'email':
                email = serializer.validated_data.get('email', user.email)
                
                device, created = EmailDevice.objects.get_or_create(
                    user=user,
                    defaults={'email': email, 'name': 'Email 2FA'}
                )
                
                if not created:
                    device.email = email
                    device.save()
                
                device.confirmed = True
                device.save()
                device.generate_challenge()
                
                return Response({
                    'message': 'Email 2FA enabled successfully. Test code sent to your email.',
                    'method': 'email',
                    'email': device.email
                }, status=status.HTTP_200_OK)
            
            elif method == 'push':
                device_token = serializer.validated_data['device_token']
                device_name = serializer.validated_data['device_name']
                device_type = serializer.validated_data['device_type']
                push_service = serializer.validated_data['push_service']
                
                device, created = PushDevice.objects.get_or_create(
                    user=user,
                    device_token=device_token,
                    defaults={
                        'device_name': device_name,
                        'device_type': device_type,
                        'push_service': push_service,
                        'name': f'Push Device - {device_name}',
                        'confirmed': True
                    }
                )
                
                if not created:
                    device.device_name = device_name
                    device.device_type = device_type
                    device.push_service = push_service
                    device.confirmed = True
                    device.save()
                
                # Send test push notification
                challenge_id = device.generate_challenge({'test': True})
                
                return Response({
                    'message': f'Push notifications enabled for {device_name}. Test notification sent.',
                    'method': 'push',
                    'device_name': device_name,
                    'challenge_id': challenge_id
                }, status=status.HTTP_200_OK)
            
            elif method == 'totp':
                # For TOTP, we need a separate setup flow with QR code
                return Response({
                    'message': 'Use /api/auth/2fa/setup-totp/ to set up authenticator app',
                    'method': 'totp'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DisableTwoFactorView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Disable 2FA methods for current user"""
        serializer = DisableTwoFactorSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            method = serializer.validated_data.get('method', 'all')
            
            if method == 'email' or method == 'all':
                EmailDevice.objects.filter(user=user).delete()
            
            if method == 'totp' or method == 'all':
                TOTPDevice.objects.filter(user=user).delete()
                
            if method == 'push' or method == 'all':
                PushDevice.objects.filter(user=user).delete()
            
            message = f'{method.upper()} 2FA disabled successfully' if method != 'all' else 'All 2FA methods disabled successfully'
            
            return Response({
                'message': message
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Verify OTP and complete login"""
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Complete the login
            login(request, user)
            profile_serializer = UserProfileSerializer(user)
            
            return Response({
                'message': 'Login successful',
                'user': profile_serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SetupTOTPView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Generate QR code for TOTP setup"""
        serializer = SetupTOTPSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            
            # Create unconfirmed TOTP device
            device = TOTPDevice.objects.create(
                user=user,
                name=f'Authenticator App - {user.username}',
                confirmed=False
            )
            
            return Response({
                'message': 'TOTP device created successfully. Please use the confirm endpoint to complete setup.',
                'device_id': device.id,
                'next_step': 'Generate a code from your authenticator app and call /api/auth/2fa/confirm-totp/ to complete setup'
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ConfirmTOTPView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Confirm TOTP setup with verification code"""
        serializer = ConfirmTOTPSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            otp_code = serializer.validated_data['otp_code']
            
            # Find unconfirmed TOTP device
            try:
                device = TOTPDevice.objects.get(user=user, confirmed=False)
            except TOTPDevice.DoesNotExist:
                return Response({
                    'error': 'No pending TOTP setup found. Please start setup first.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify the code
            if device.verify_token(otp_code):
                device.confirmed = True
                device.save()
                
                return Response({
                    'message': 'TOTP 2FA enabled successfully',
                    'method': 'totp'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Invalid verification code. Please try again.'
                }, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RegisterPushDeviceView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Register a new push notification device"""
        serializer = RegisterPushDeviceSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            
            device = PushDevice.objects.create(
                user=user,
                device_token=serializer.validated_data['device_token'],
                device_name=serializer.validated_data['device_name'],
                device_type=serializer.validated_data['device_type'],
                push_service=serializer.validated_data['push_service'],
                name=f"Push Device - {serializer.validated_data['device_name']}",
                confirmed=True
            )
            
            # Send test notification
            challenge_id = device.generate_challenge({'test': True, 'welcome': True})
            
            return Response({
                'message': f'Push device "{device.device_name}" registered successfully',
                'device_id': device.id,
                'test_challenge_id': challenge_id
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ApprovePushChallengeView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Approve or deny a push notification challenge"""
        serializer = ApprovePushChallengeSerializer(data=request.data)
        if serializer.is_valid():
            challenge_id = serializer.validated_data['challenge_id']
            approved = serializer.validated_data['approved']
            
            if approved:
                return Response({
                    'message': 'Challenge approved successfully',
                    'challenge_id': challenge_id
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'message': 'Challenge denied',
                    'challenge_id': challenge_id
                }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserPreferencesView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get user 2FA preferences"""
        try:
            preferences = UserDevicePreference.objects.get(user=request.user)
            serializer = UserPreferencesSerializer(preferences)
            return Response(serializer.data)
        except UserDevicePreference.DoesNotExist:
            # Return default preferences
            return Response({
                'primary_method': 'email',
                'fallback_methods': ['totp', 'push'],
                'require_2fa_for_sensitive_actions': True,
                'remember_device_days': 30
            })
    
    def post(self, request):
        """Update user 2FA preferences"""
        preferences, created = UserDevicePreference.objects.get_or_create(
            user=request.user,
            defaults={
                'primary_method': 'email',
                'fallback_methods': ['totp', 'push'],
                'require_2fa_for_sensitive_actions': True,
                'remember_device_days': 30
            }
        )
        
        serializer = UserPreferencesSerializer(preferences, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Preferences updated successfully',
                'preferences': serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)