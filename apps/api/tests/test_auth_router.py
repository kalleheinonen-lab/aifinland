"""Integration tests for auth router using FastAPI TestClient.

Kills: wrong status codes, missing envelope fields, password policy bypass,
duplicate email not caught, invalid token accepted, MFA flow broken.
"""

from unittest.mock import AsyncMock

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.main import app
from app.middleware.auth_middleware import (
    _get_token_service as _middleware_get_token_service,
)
from app.routers.auth import _get_auth_service, _get_mfa_service, _get_token_service
from app.services.token_service import TokenService

# --- Test fixtures ---


@pytest.fixture
def rsa_key_pair() -> tuple[str, str]:
    """Generate an RSA key pair for testing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )

    return private_pem, public_pem


@pytest.fixture
def token_service(rsa_key_pair: tuple[str, str]) -> TokenService:
    """Create a TokenService with test keys."""
    private_key, public_key = rsa_key_pair
    return TokenService(private_key=private_key, public_key=public_key)


@pytest.fixture
def mock_auth_service() -> AsyncMock:
    """Create a mock AuthService."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_mfa_service() -> AsyncMock:
    """Create a mock MFAService."""
    service = AsyncMock()
    return service


@pytest.fixture
def client(
    mock_auth_service: AsyncMock,
    mock_mfa_service: AsyncMock,
    token_service: TokenService,
) -> TestClient:
    """Create a test client with dependency overrides."""
    import os

    os.environ.setdefault("CORS_ALLOWED_ORIGINS", "http://localhost:3000")

    app.dependency_overrides[_get_auth_service] = lambda: mock_auth_service
    app.dependency_overrides[_get_mfa_service] = lambda: mock_mfa_service
    app.dependency_overrides[_get_token_service] = lambda: token_service
    app.dependency_overrides[_middleware_get_token_service] = lambda: token_service

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# --- Helper ---


def _auth_header(token_service: TokenService, user_id: str = "user-123") -> dict:
    """Build an Authorization header with a valid JWT."""
    token = token_service.create_access_token(
        user_id=user_id, org_id=None, roles=["user"]
    )
    return {"Authorization": f"Bearer {token}"}


# --- Register Tests ---


class TestRegister:
    """Tests for POST /v1/auth/register."""

    def test_ac1_register_success_returns_201(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """AC-1: Register with valid data returns 201 with tokens and user."""
        # AC-1: expect 201 with {data: {access_token, refresh_token, user}}
        mock_auth_service.register.return_value = {
            "access_token": "access-tok",
            "refresh_token": "refresh-tok",
            "user_id": "user-123",
            "email": "new@example.com",
        }

        response = client.post(
            "/v1/auth/register",
            json={
                "email": "new@example.com",
                "password": "SecurePass123!",
                "display_name": "New User",
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["data"]["access_token"] == "access-tok"
        assert body["data"]["refresh_token"] == "refresh-tok"
        assert body["data"]["user"]["email"] == "new@example.com"
        assert body["meta"]["requestId"] is not None
        assert body["meta"]["timestamp"] is not None
        assert body["error"] is None

    def test_ac2_register_duplicate_email_returns_409(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """AC-2: Register with existing email returns 409."""
        from app.services.auth_service import EmailAlreadyExistsError

        # AC-2: expect 409 with error code EMAIL_EXISTS
        mock_auth_service.register.side_effect = EmailAlreadyExistsError(
            "Email already registered"
        )

        response = client.post(
            "/v1/auth/register",
            json={
                "email": "existing@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 409

    def test_register_password_too_short_returns_422(
        self,
        client: TestClient,
    ) -> None:
        """Password shorter than 12 chars is rejected at validation."""
        response = client.post(
            "/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "Short1!",
            },
        )

        # Pydantic validation error -> 422
        assert response.status_code == 422

    def test_register_password_no_uppercase_returns_422(
        self,
        client: TestClient,
    ) -> None:
        """Password without uppercase is rejected."""
        response = client.post(
            "/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "nouppercase123!",
            },
        )

        assert response.status_code == 422

    def test_register_password_no_digit_returns_422(
        self,
        client: TestClient,
    ) -> None:
        """Password without digit is rejected."""
        response = client.post(
            "/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "NoDigitHere!!aa",
            },
        )

        assert response.status_code == 422

    def test_register_password_no_symbol_returns_422(
        self,
        client: TestClient,
    ) -> None:
        """Password without symbol is rejected."""
        response = client.post(
            "/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "NoSymbolHere12a",
            },
        )

        assert response.status_code == 422


# --- Login Tests ---


class TestLogin:
    """Tests for POST /v1/auth/login."""

    def test_ac3_login_success_returns_tokens(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """AC-3: Successful login returns 200 with tokens."""
        # AC-3: expect 200 with access_token, refresh_token, user
        mock_auth_service.login.return_value = {
            "access_token": "access-tok",
            "refresh_token": "refresh-tok",
            "user_id": "user-123",
            "email": "user@example.com",
        }

        response = client.post(
            "/v1/auth/login",
            json={"email": "user@example.com", "password": "CorrectPass1!"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["access_token"] == "access-tok"
        assert body["data"]["refresh_token"] == "refresh-tok"
        assert body["data"]["user"]["email"] == "user@example.com"
        assert body["error"] is None

    def test_ac4_login_wrong_password_returns_401(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """AC-4: Wrong password returns 401 with generic message."""
        from app.services.auth_service import InvalidCredentialsError

        # AC-4: expect 401 with code INVALID_CREDENTIALS
        mock_auth_service.login.side_effect = InvalidCredentialsError(
            "Invalid email or password"
        )

        response = client.post(
            "/v1/auth/login",
            json={"email": "user@example.com", "password": "WrongPass1!"},
        )

        assert response.status_code == 401

    def test_ac5_login_locked_account_returns_401(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """AC-5: Locked account returns 401 (same as invalid credentials)."""
        from app.services.auth_service import AccountLockedError

        # AC-5: expect 401 (generic, no info leak about lock)
        mock_auth_service.login.side_effect = AccountLockedError(
            "Account temporarily locked"
        )

        response = client.post(
            "/v1/auth/login",
            json={"email": "locked@example.com", "password": "AnyPass123!"},
        )

        assert response.status_code == 401

    def test_ac6_login_mfa_required_returns_mfa_token(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """AC-6: Login with MFA enabled returns mfa_required response."""
        from app.services.auth_service import MfaChallengeRequiredError

        # AC-6: expect 200 with {mfa_required: true, mfa_token: ...}
        mock_auth_service.login.side_effect = MfaChallengeRequiredError("user-456")

        response = client.post(
            "/v1/auth/login",
            json={"email": "mfa@example.com", "password": "CorrectPass1!"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["mfa_required"] is True
        assert body["data"]["mfa_token"] is not None
        assert len(body["data"]["mfa_token"]) > 0


# --- MFA Tests ---


class TestMFAVerify:
    """Tests for POST /v1/auth/mfa/verify."""

    def test_ac7_mfa_verify_success_returns_tokens(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
        mock_mfa_service: AsyncMock,
        token_service: TokenService,
    ) -> None:
        """AC-7: Valid MFA code returns full tokens."""
        # Create a valid MFA challenge token
        mfa_token = token_service.create_access_token(
            user_id="user-789", org_id=None, roles=["mfa_challenge"]
        )

        # AC-7: expect 200 with full tokens after MFA verification
        mock_mfa_service.verify_mfa.return_value = True
        mock_auth_service.issue_tokens_for_user.return_value = {
            "access_token": "full-access-tok",
            "refresh_token": "full-refresh-tok",
            "user_id": "user-789",
            "email": "mfa@example.com",
        }

        response = client.post(
            "/v1/auth/mfa/verify",
            json={"mfa_token": mfa_token, "code": "123456"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["access_token"] == "full-access-tok"
        assert body["data"]["refresh_token"] == "full-refresh-tok"

    def test_mfa_verify_invalid_code_returns_401(
        self,
        client: TestClient,
        mock_mfa_service: AsyncMock,
        token_service: TokenService,
    ) -> None:
        """Invalid MFA code returns 401."""
        mfa_token = token_service.create_access_token(
            user_id="user-789", org_id=None, roles=["mfa_challenge"]
        )

        mock_mfa_service.verify_mfa.return_value = False

        response = client.post(
            "/v1/auth/mfa/verify",
            json={"mfa_token": mfa_token, "code": "000000"},
        )

        assert response.status_code == 401

    def test_mfa_verify_invalid_token_returns_401(
        self,
        client: TestClient,
    ) -> None:
        """Invalid MFA token returns 401."""
        response = client.post(
            "/v1/auth/mfa/verify",
            json={"mfa_token": "invalid-token", "code": "123456"},
        )

        assert response.status_code == 401


class TestMFASetup:
    """Tests for POST /v1/auth/mfa/setup."""

    def test_mfa_setup_returns_secret_and_codes(
        self,
        client: TestClient,
        mock_mfa_service: AsyncMock,
        token_service: TokenService,
    ) -> None:
        """MFA setup returns secret, provisioning_uri, and backup_codes."""
        mock_mfa_service.setup_mfa.return_value = {
            "secret": "JBSWY3DPEHPK3PXP",
            "provisioning_uri": "otpauth://totp/AI%20Finland:user@test.com?secret=JBSWY3DPEHPK3PXP&issuer=AI+Finland",
            "backup_codes": ["CODE1234", "CODE5678"],
        }

        headers = _auth_header(token_service)
        response = client.post("/v1/auth/mfa/setup", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["secret"] == "JBSWY3DPEHPK3PXP"
        assert body["data"]["provisioning_uri"].startswith("otpauth://")
        assert len(body["data"]["backup_codes"]) == 2

    def test_mfa_setup_requires_auth(
        self,
        client: TestClient,
    ) -> None:
        """MFA setup without auth returns 401."""
        response = client.post("/v1/auth/mfa/setup")

        assert response.status_code == 401


class TestMFASetupConfirm:
    """Tests for POST /v1/auth/mfa/setup/confirm."""

    def test_mfa_setup_confirm_success(
        self,
        client: TestClient,
        mock_mfa_service: AsyncMock,
        token_service: TokenService,
    ) -> None:
        """MFA setup confirm with valid code returns success."""
        mock_mfa_service.confirm_mfa_setup.return_value = True

        headers = _auth_header(token_service)
        response = client.post(
            "/v1/auth/mfa/setup/confirm",
            json={"code": "123456"},
            headers=headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["mfa_enabled"] is True

    def test_mfa_setup_confirm_invalid_code_returns_400(
        self,
        client: TestClient,
        mock_mfa_service: AsyncMock,
        token_service: TokenService,
    ) -> None:
        """MFA setup confirm with invalid code returns 400."""
        from app.services.mfa_service import InvalidMFACodeError

        mock_mfa_service.confirm_mfa_setup.side_effect = InvalidMFACodeError(
            "Invalid TOTP code"
        )

        headers = _auth_header(token_service)
        response = client.post(
            "/v1/auth/mfa/setup/confirm",
            json={"code": "000000"},
            headers=headers,
        )

        assert response.status_code == 400


# --- Refresh Token Tests ---


class TestRefreshToken:
    """Tests for POST /v1/auth/refresh."""

    def test_ac8_refresh_token_rotation(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
        token_service: TokenService,
    ) -> None:
        """AC-8: Refresh token rotation returns new token pair."""
        # AC-8: expect new access_token and refresh_token
        mock_auth_service.refresh_token.return_value = {
            "access_token": "new-access-tok",
            "refresh_token": "new-refresh-tok",
        }

        headers = _auth_header(token_service)
        response = client.post(
            "/v1/auth/refresh",
            json={"refresh_token": "old-refresh-tok"},
            headers=headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["access_token"] == "new-access-tok"
        assert body["data"]["refresh_token"] == "new-refresh-tok"

    def test_refresh_invalid_token_returns_401(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
        token_service: TokenService,
    ) -> None:
        """Invalid refresh token returns 401."""
        from app.services.auth_service import InvalidTokenError

        mock_auth_service.refresh_token.side_effect = InvalidTokenError(
            "Invalid refresh token"
        )

        headers = _auth_header(token_service)
        response = client.post(
            "/v1/auth/refresh",
            json={"refresh_token": "invalid-tok"},
            headers=headers,
        )

        assert response.status_code == 401


# --- Logout Tests ---


class TestLogout:
    """Tests for POST /v1/auth/logout."""

    def test_ac9_logout_returns_204(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
        token_service: TokenService,
    ) -> None:
        """AC-9: Logout returns 204 and invalidates refresh token."""
        # AC-9: expect 204 No Content
        mock_auth_service.logout.return_value = True

        headers = _auth_header(token_service)
        headers["Content-Type"] = "application/json"
        response = client.post(
            "/v1/auth/logout",
            content='{"refresh_token": "tok-to-revoke"}',
            headers=headers,
        )

        assert response.status_code == 204

    def test_logout_requires_auth(
        self,
        client: TestClient,
    ) -> None:
        """Logout without auth returns 401."""
        response = client.post("/v1/auth/logout")

        assert response.status_code == 401


# --- Password Reset Tests ---


class TestPasswordReset:
    """Tests for password reset endpoints."""

    def test_ac10_password_reset_request_always_200(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """AC-10: Password reset request always returns 200 (silent success)."""
        # AC-10: expect 200 regardless of email existence
        mock_auth_service.request_password_reset.return_value = None

        response = client.post(
            "/v1/auth/password-reset/request",
            json={"email": "anyone@example.com"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["error"] is None

    def test_password_reset_confirm_success(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """Password reset confirm with valid token returns 200."""
        mock_auth_service.confirm_password_reset.return_value = True

        response = client.post(
            "/v1/auth/password-reset/confirm",
            json={"token": "valid-reset-token", "new_password": "NewSecure123!"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["error"] is None

    def test_password_reset_confirm_invalid_token_returns_400(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """Password reset confirm with invalid token returns 400."""
        from app.services.auth_service import InvalidTokenError

        mock_auth_service.confirm_password_reset.side_effect = InvalidTokenError(
            "Invalid or expired reset token"
        )

        response = client.post(
            "/v1/auth/password-reset/confirm",
            json={"token": "invalid-token", "new_password": "NewSecure123!"},
        )

        assert response.status_code == 400

    def test_password_reset_confirm_weak_password_returns_422(
        self,
        client: TestClient,
    ) -> None:
        """Password reset with weak password returns 422."""
        response = client.post(
            "/v1/auth/password-reset/confirm",
            json={"token": "valid-token", "new_password": "weak"},
        )

        assert response.status_code == 422


# --- Verify Email Tests ---


class TestVerifyEmail:
    """Tests for POST /v1/auth/verify-email."""

    def test_verify_email_success(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """Verify email with valid token returns 200."""
        mock_auth_service.verify_email.return_value = True

        response = client.post(
            "/v1/auth/verify-email",
            json={"token": "valid-verification-token"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["verified"] is True

    def test_verify_email_invalid_token_returns_400(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """Verify email with invalid token returns 400."""
        from app.services.auth_service import InvalidTokenError

        mock_auth_service.verify_email.side_effect = InvalidTokenError(
            "Invalid or expired verification token"
        )

        response = client.post(
            "/v1/auth/verify-email",
            json={"token": "invalid-token"},
        )

        assert response.status_code == 400


# --- Auth Middleware Tests ---


class TestAuthMiddleware:
    """Tests for auth middleware (get_current_user)."""

    def test_missing_token_returns_401(
        self,
        client: TestClient,
    ) -> None:
        """Missing Authorization header returns 401."""
        response = client.post("/v1/auth/mfa/setup")

        assert response.status_code == 401

    def test_invalid_token_returns_401(
        self,
        client: TestClient,
    ) -> None:
        """Invalid JWT returns 401."""
        response = client.post(
            "/v1/auth/mfa/setup",
            headers={"Authorization": "Bearer invalid-jwt-token"},
        )

        assert response.status_code == 401

    def test_admin_without_mfa_gets_403_on_protected_endpoint(
        self,
        client: TestClient,
        token_service: TokenService,
    ) -> None:
        """Admin user without MFA enabled gets 403 MFA_SETUP_REQUIRED."""
        # Create token for admin without mfa_enabled
        # Note: The middleware checks payload.get("mfa_enabled", False)
        # We need to create a token that has admin role but no mfa_enabled
        token = token_service.create_access_token(
            user_id="admin-user",
            org_id=None,
            roles=["admin"],
        )

        # Use a non-MFA-setup endpoint that requires auth
        # The logout endpoint requires auth via get_current_user
        response = client.post(
            "/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Admin without MFA should get 403 on non-MFA-setup endpoints
        assert response.status_code == 403

    def test_admin_without_mfa_allowed_on_mfa_setup(
        self,
        client: TestClient,
        mock_mfa_service: AsyncMock,
        token_service: TokenService,
    ) -> None:
        """Admin user without MFA is allowed on /v1/auth/mfa/setup."""
        token = token_service.create_access_token(
            user_id="admin-user",
            org_id=None,
            roles=["admin"],
        )

        mock_mfa_service.setup_mfa.return_value = {
            "secret": "SECRET",
            "provisioning_uri": "otpauth://totp/test",
            "backup_codes": ["CODE1"],
        }

        response = client.post(
            "/v1/auth/mfa/setup",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Should be allowed (not 403)
        assert response.status_code == 200


# --- Response Envelope Tests ---


class TestResponseEnvelope:
    """Tests for response envelope format."""

    def test_success_response_has_correct_envelope(
        self,
        client: TestClient,
        mock_auth_service: AsyncMock,
    ) -> None:
        """Success responses have {data, meta, error: null} envelope."""
        mock_auth_service.request_password_reset.return_value = None

        response = client.post(
            "/v1/auth/password-reset/request",
            json={"email": "test@example.com"},
        )

        body = response.json()
        assert "data" in body
        assert "meta" in body
        assert "error" in body
        assert body["error"] is None
        assert "requestId" in body["meta"]
        assert "timestamp" in body["meta"]
