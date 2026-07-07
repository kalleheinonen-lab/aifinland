"""JWT token service with RS256 algorithm pinning (SR-001)."""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.config import get_jwt_private_key, get_jwt_public_key

logger = logging.getLogger(__name__)

# Security: access token lifetime 24h, refresh token 30d
ACCESS_TOKEN_EXPIRY = timedelta(hours=24)
REFRESH_TOKEN_EXPIRY = timedelta(days=30)


class TokenVerificationError(Exception):
    """Raised when a token cannot be verified."""


class TokenService:
    """JWT token service with RS256 algorithm pinning.

    Security invariant (SR-001): jwt.decode() MUST specify
    algorithms=['RS256']. The token's alg header is NEVER trusted.
    """

    def __init__(
        self,
        private_key: str | None = None,
        public_key: str | None = None,
    ) -> None:
        """Initialize with RSA key pair.

        Args:
            private_key: RSA private key in PEM format. Reads from env if None.
            public_key: RSA public key in PEM format. Reads from env if None.
        """
        self._private_key = private_key or get_jwt_private_key()
        self._public_key = public_key or get_jwt_public_key()

    def create_access_token(
        self,
        user_id: str,
        org_id: str | None = None,
        roles: list[str] | None = None,
    ) -> str:
        """Create an RS256-signed JWT access token.

        Payload includes: sub, org, roles, exp, jti, iat.
        """
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            "sub": user_id,
            "org": org_id,
            "roles": roles or [],
            "exp": now + ACCESS_TOKEN_EXPIRY,
            "iat": now,
            "jti": str(uuid.uuid4()),
        }
        token: str = jwt.encode(
            payload,
            self._private_key,
            algorithm="RS256",
        )
        logger.info("Access token issued for user_id=%s", user_id)
        return token

    def create_refresh_token(self) -> str:
        """Create an opaque refresh token (UUID-based).

        The token is stored in Valkey by the session service.
        """
        return str(uuid.uuid4())

    def verify_access_token(self, token: str) -> dict[str, Any]:
        """Verify a JWT access token.

        Security invariant (SR-001): Algorithm is pinned to RS256.
        Tokens with any other algorithm header are rejected.

        Args:
            token: The JWT string to verify.

        Returns:
            The decoded payload dictionary.

        Raises:
            TokenVerificationError: If the token is invalid or uses wrong algorithm.
        """
        try:
            # SECURITY: Algorithm pinning - NEVER trust the token's alg header
            payload: dict[str, Any] = jwt.decode(
                token,
                self._public_key,
                algorithms=["RS256"],
            )
            return payload
        except jwt.InvalidAlgorithmError as e:
            logger.warning("Token rejected: invalid algorithm")
            raise TokenVerificationError("Invalid token algorithm") from e
        except jwt.ExpiredSignatureError as e:
            logger.info("Token rejected: expired")
            raise TokenVerificationError("Token has expired") from e
        except jwt.InvalidTokenError as e:
            logger.warning("Token rejected: invalid token")
            raise TokenVerificationError("Invalid token") from e
