from django.urls import path
from . import views

app_name = 'authn'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change_password'),
    path('me/', views.me, name='me'),
    
    # 2FA endpoints
    path('2fa/status/', views.TwoFactorStatusView.as_view(), name='2fa_status'),
    path('2fa/enable/', views.EnableTwoFactorView.as_view(), name='2fa_enable'),
    path('2fa/disable/', views.DisableTwoFactorView.as_view(), name='2fa_disable'),
    path('2fa/verify/', views.VerifyOTPView.as_view(), name='2fa_verify'),
    
    # TOTP (Authenticator App) endpoints
    path('2fa/setup-totp/', views.SetupTOTPView.as_view(), name='2fa_setup_totp'),
    path('2fa/confirm-totp/', views.ConfirmTOTPView.as_view(), name='2fa_confirm_totp'),
    
    # Push notification endpoints
    path('2fa/register-push/', views.RegisterPushDeviceView.as_view(), name='2fa_register_push'),
    path('2fa/approve-push/', views.ApprovePushChallengeView.as_view(), name='2fa_approve_push'),
    
    # User preferences
    path('2fa/preferences/', views.UserPreferencesView.as_view(), name='2fa_preferences'),
]