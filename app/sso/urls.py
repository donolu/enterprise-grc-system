"""
SSO URL patterns.
"""

from django.urls import path
from . import views

app_name = 'sso'

urlpatterns = [
    # SSO selection and status
    path('login/', views.sso_login_select, name='login_select'),
    path('logout/', views.sso_logout, name='logout'),
    path('profile/', views.sso_profile, name='profile'),
    path('status/', views.sso_status, name='status'),

    # SAML endpoints
    path('saml/login/<uuid:provider_id>/', views.saml_login, name='saml_login'),
    path('saml/acs/<uuid:provider_id>/', views.saml_acs, name='saml_acs'),
    path('saml/sls/<uuid:provider_id>/', views.saml_sls, name='saml_sls'),
    path('saml/metadata/<uuid:provider_id>/', views.saml_metadata, name='saml_metadata'),

    # OAuth endpoints (placeholder)
    path('oauth/login/<uuid:provider_id>/', views.oauth_login, name='oauth_login'),
    path('oauth/callback/<uuid:provider_id>/', views.oauth_callback, name='oauth_callback'),
]