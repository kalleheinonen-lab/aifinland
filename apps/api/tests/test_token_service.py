"""Tests for TokenService with RS256 algorithm pinning.

Kills: algorithm confusion attack (HS256 token accepted), expired token accepted,
tampered payload accepted, wrong key accepted.
"""

import time
import uuid
from unittest.mock import patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.services.token_service import TokenService, TokenVerificationError


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

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return private_pem, public_pem


@pytest.fixture
def token_service(rsa_key_pair: tuple[str, str]) -> TokenService:
    """Create a TokenService with test keys."""
    private_key, public_key = rsa_key_pair
    return TokenService(private_key=private_key, public_key=public_key)


class TestCreateAccessToken:
    """Tests for access token creation."""

    def test_creates_valid_jwt(self, token_service: TokenService) -> None:
        """AC-1: create_access_token produces a valid RS256 JWT."""
        token = token_service.create_access_token(
            user_id="user-123",
            org_id="org-456",
            roles=["admin"],
        )

        assert isinstance(token, str)
        assert len(token.split(".")) == 3  # JWT has 3 parts

    def test_payload_contains_required_claims(
        self, token_service: TokenService
    ) -> None:
        """AC-1: Access token payload includes sub, org, roles, exp, jti, iat."""
        token = token_service.create_access_token(
            user_id="user-123",
            org_id="org-456",
            roles=["admin", "user"],
        )

        payload = token_service.verify_access_token(token)

        assert payload["sub"] == "user-123"
        assert payload["org"] == "org-456"
        assert payload["roles"] == ["admin", "user"]
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload
        # jti should be a valid UUID
        uuid.UUID(payload["jti"])

    def test_default_roles_empty_list(self, token_service: TokenService) -> None:
        """Roles default to empty list when not provided."""
        token = token_service.create_access_token(user_id="user-123")
        payload = token_service.verify_access_token(token)
        assert payload["roles"] == []

    def test_org_id_can_be_none(self, token_service: TokenService) -> None:
        """Org ID can be None for users without an organization."""
        token = token_service.create_access_token(user_id="user-123", org_id=None)
        payload = token_service.verify_access_token(token)
        assert payload["org"] is None


class TestVerifyAccessToken:
    """Tests for access token verification with algorithm pinning."""

    def test_verifies_valid_rs256_token(
        self, token_service: TokenService
    ) -> None:
        """Valid RS256 token is accepted."""
        token = token_service.create_access_token(user_id="user-123")
        payload = token_service.verify_access_token(token)
        assert payload["sub"] == "user-123"

    def test_ac4_rejects_hs256_algorithm_confusion(
        self, token_service: TokenService, rsa_key_pair: tuple[str, str]
    ) -> None:
        """AC-4: Algorithm confusion attack - HS256 token is REJECTED.

        This is the critical SR-001 security invariant. Even if an attacker
        crafts a valid HS256 token, the server MUST reject it because only
        RS256 is accepted via algorithm pinning.
        """
        # Attacker creates an HS256 token using an arbitrary secret
        malicious_payload = {
            "sub": "admin-user",
            "roles": ["super_admin"],
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
            "jti": str(uuid.uuid4()),
        }
        malicious_token = jwt.encode(
            malicious_payload,
            "attacker-secret-key",
            algorithm="HS256",
        )

        # AC-4: expect rejection with TokenVerificationError
        with pytest.raises(TokenVerificationError):
            token_service.verify_access_token(malicious_token)

    def test_rejects_expired_token(
        self, rsa_key_pair: tuple[str, str]
    ) -> None:
        """Expired tokens are rejected."""
        private_key, public_key = rsa_key_pair
        service = TokenService(private_key=private_key, public_key=public_key)

        # Create a token that's already expired
        expired_payload = {
            "sub": "user-123",
            "org": None,
            "roles": [],
            "exp": int(time.time()) - 3600,  # 1 hour ago
            "iat": int(time.time()) - 7200,
            "jti": str(uuid.uuid4()),
        }
        expired_token = jwt.encode(expired_payload, private_key, algorithm="RS256")

        with pytest.raises(TokenVerificationError, match="expired"):
            service.verify_access_token(expired_token)

    def test_rejects_token_signed_with_wrong_key(
        self, token_service: TokenService
    ) -> None:
        """Token signed with a different private key is rejected."""
        # Generate a different key pair
        other_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        other_private_pem = other_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

        # Sign with wrong key
        payload = {
            "sub": "user-123",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
            "jti": str(uuid.uuid4()),
        }
        wrong_token = jwt.encode(payload, other_private_pem, algorithm="RS256")

        with pytest.raises(TokenVerificationError):
            token_service.verify_access_token(wrong_token)

    def test_rejects_none_algorithm(
        self, token_service: TokenService
    ) -> None:
        """Token with 'none' algorithm is rejected."""
        # Manually craft a token with alg=none
        import base64
        import json

        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "none", "typ": "JWT"}).encode()
        ).rstrip(b"=")
        payload = base64.urlsafe_b64encode(
            json.dumps({"sub": "admin", "roles": ["super_admin"]}).encode()
        ).rstrip(b"=")
        none_token = f"{header.decode()}.{payload.decode()}."

        with pytest.raises(TokenVerificationError):
            token_service.verify_access_token(none_token)


class TestCreateRefreshToken:
    """Tests for refresh token creation."""

    def test_creates_opaque_token(self, token_service: TokenService) -> None:
        """Refresh token is an opaque UUID string."""
        token = token_service.create_refresh_token()
        # Should be a valid UUID
        uuid.UUID(token)

    def test_creates_unique_tokens(self, token_service: TokenService) -> None:
        """Each refresh token is unique."""
        tokens = {token_service.create_refresh_token() for _ in range(100)}
        assert len(tokens) == 100


class TestTokenServiceInit:
    """Tests for TokenService initialization."""

    def test_raises_if_private_key_not_set(self) -> None:
        """Startup assertion: throws if JWT_PRIVATE_KEY is unset."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(Exception, match="JWT_PRIVATE_KEY"):
                TokenService()

    def test_raises_if_public_key_not_set(
        self, rsa_key_pair: tuple[str, str]
    ) -> None:
        """Startup assertion: throws if JWT_PUBLIC_KEY is unset."""
        private_key, _ = rsa_key_pair
        with patch.dict("os.environ", {"JWT_PRIVATE_KEY": private_key}, clear=True):
            with pytest.raises(Exception, match="JWT_PUBLIC_KEY"):
                TokenService()
