"""Rate limiting service for failed login attempts."""

from __future__ import annotations

import logging
from typing import Any, Protocol

from app.config import get_valkey_url

logger = logging.getLogger(__name__)

# Rate limit configuration
MAX_FAILED_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SECONDS = 15 * 60  # 15 minutes


class ValkeyClient(Protocol):
    """Protocol for Valkey client operations used by RateLimitService."""

    def get(self, name: str) -> Any: ...  # noqa: E704
    def incr(self, name: str) -> Any: ...  # noqa: E704
    def expire(self, name: str, time: int) -> Any: ...  # noqa: E704
    def delete(self, *names: str) -> Any: ...  # noqa: E704
    def ttl(self, name: str) -> Any: ...  # noqa: E704


class RateLimitService:
    """Tracks failed login attempts and enforces rate limits.

    Uses Valkey key pattern: login_failures:{email} with 15min TTL.
    After 5 failures, the account is blocked.
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

    def _failure_key(self, email: str) -> str:
        """Build the Valkey key for tracking login failures."""
        return f"login_failures:{email}"

    def check_login_rate_limit(self, email: str) -> bool:
        """Check if login is allowed for the given email.

        Returns:
            True if login is allowed, False if blocked (rate limited).
        """
        key = self._failure_key(email)
        raw_count = self._client.get(key)
        if raw_count is None:
            return True

        count = int(raw_count)
        if count >= MAX_FAILED_ATTEMPTS:
            # Security: log alert without credentials
            logger.warning(
                "Rate limit triggered: login blocked for "
                "email_hash=%s after %d failures",
                hash(email),
                count,
            )
            return False

        return True

    def record_failed_attempt(self, email: str) -> None:
        """Record a failed login attempt.

        Increments the failure counter and sets/refreshes the TTL.
        """
        key = self._failure_key(email)
        count = self._client.incr(key)

        # Set TTL on first failure or refresh it
        if count == 1:
            self._client.expire(key, RATE_LIMIT_WINDOW_SECONDS)

        logger.info(
            "Failed login attempt recorded: email_hash=%s, count=%d",
            hash(email),
            count,
        )

    def reset_on_success(self, email: str) -> None:
        """Reset the failure counter on successful login."""
        key = self._failure_key(email)
        self._client.delete(key)
