"""Session management service using Valkey."""

from __future__ import annotations

import logging
from typing import Any, Protocol

from app.config import get_valkey_url

logger = logging.getLogger(__name__)

# Maximum concurrent sessions per user
MAX_SESSIONS_PER_USER = 5

# Refresh token TTL in seconds (30 days)
REFRESH_TOKEN_TTL_SECONDS = 30 * 24 * 60 * 60


class ValkeyClient(Protocol):
    """Protocol for Valkey client operations used by SessionService."""

    def sadd(self, name: str, *values: str) -> int: ...  # noqa: E704
    def srem(self, name: str, *values: str) -> int: ...  # noqa: E704
    def sismember(self, name: str, value: str) -> Any: ...  # noqa: E704
    def smembers(self, name: str) -> Any: ...  # noqa: E704
    def scard(self, name: str) -> int: ...  # noqa: E704
    def delete(self, *names: str) -> int: ...  # noqa: E704
    def set(self, name: str, value: str, ex: int | None = None) -> Any: ...  # noqa: E704
    def get(self, name: str) -> Any: ...  # noqa: E704
    def expire(self, name: str, time: int) -> Any: ...  # noqa: E704
    def spop(self, name: str, count: int | None = None) -> Any: ...  # noqa: E704


class SessionService:
    """Manages user sessions in Valkey.

    Sessions are tracked as a set per user: sessions:{user_id}.
    Enforces max 5 concurrent sessions per user.
    """

    def __init__(self, valkey_client: ValkeyClient | None = None) -> None:
        """Initialize with a Valkey client.

        Args:
            valkey_client: Valkey client instance. If None, creates one from VALKEY_URL.
        """
        if valkey_client is not None:
            self._client = valkey_client
        else:
            import valkey

            url = get_valkey_url()
            self._client = valkey.from_url(url)  # type: ignore[no-untyped-call]

    def _session_key(self, user_id: str) -> str:
        """Build the Valkey key for a user's session set."""
        return f"sessions:{user_id}"

    def create_session(self, user_id: str, refresh_token: str) -> None:
        """Add a refresh token to the user's session set.

        Enforces max 5 concurrent sessions. If at limit, evicts one session.
        """
        key = self._session_key(user_id)
        current_count = self._client.scard(key)

        if current_count >= MAX_SESSIONS_PER_USER:
            # Evict oldest (pop one from set)
            self._client.spop(key, 1)
            logger.info(
                "Session limit reached for user_id=%s, evicted oldest session",
                user_id,
            )

        self._client.sadd(key, refresh_token)
        self._client.expire(key, REFRESH_TOKEN_TTL_SECONDS)
        logger.info("Session created for user_id=%s", user_id)

    def revoke_session(self, user_id: str, refresh_token: str) -> None:
        """Remove a specific refresh token from the user's session set."""
        key = self._session_key(user_id)
        self._client.srem(key, refresh_token)
        logger.info("Session revoked for user_id=%s", user_id)

    def revoke_all_sessions(self, user_id: str) -> None:
        """Remove all sessions for a user."""
        key = self._session_key(user_id)
        self._client.delete(key)
        logger.info("All sessions revoked for user_id=%s", user_id)

    def is_valid_session(self, user_id: str, refresh_token: str) -> bool:
        """Check if a refresh token is in the user's active session set."""
        key = self._session_key(user_id)
        return bool(self._client.sismember(key, refresh_token))
