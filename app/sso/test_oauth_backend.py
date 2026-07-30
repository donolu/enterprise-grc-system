from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import Mock, patch

from sso.oauth_backends import OAuthBackend


def test_oauth_backend_does_not_store_provider_refresh_token():
    tenant = SimpleNamespace(id=1)
    oauth_config = SimpleNamespace()
    sso_provider = SimpleNamespace(
        id=uuid4(),
        name="OIDC",
        oauth_config=oauth_config,
    )
    user = SimpleNamespace(email="oauth-user@example.com")
    sso_session = SimpleNamespace(id=uuid4())
    request = SimpleNamespace(
        META={
            "HTTP_USER_AGENT": "pytest",
            "REMOTE_ADDR": "127.0.0.1",
        },
        session={},
    )
    token_data = {
        "access_token": "access-token",
        "refresh_token": "provider-refresh-token",
        "token_type": "Bearer",
    }

    with (
        patch("sso.oauth_backends.get_tenant_from_request", return_value=tenant),
        patch("sso.oauth_backends.SSOProvider.objects.get", return_value=sso_provider),
        patch(
            "sso.oauth_backends.SSOSession.objects.create", return_value=sso_session
        ) as create_session,
        patch.object(OAuthBackend, "_exchange_code_for_token", return_value=token_data),
        patch.object(OAuthBackend, "_get_user_info", return_value={"email": user.email}),
        patch.object(OAuthBackend, "_get_or_create_user", return_value=user),
        patch("sso.oauth_backends.SSOAuditLog.get_client_ip", return_value="127.0.0.1"),
        patch("sso.oauth_backends.SSOAuditLog.log_event"),
    ):
        authenticated_user = OAuthBackend().authenticate(
            request,
            oauth_code="auth-code",
            oauth_provider_id=sso_provider.id,
        )

    assert authenticated_user == user
    assert create_session.call_count == 1
    created_session_id = create_session.call_args.kwargs["sso_session_id"]
    assert created_session_id.startswith("oauth-")
    assert created_session_id != "provider-refresh-token"
    assert request.session["sso_session_id"] == str(sso_session.id)
