"""Authentication service orchestrating login, registration, and session management."""

import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.rate_limit_service import RateLimitService
from app.services.session_service import SessionService
from app.services.token_service import TokenService

logger = logging.getLogger(__name__)

# bcrypt cost factor 12 (~200ms per hash)
BCRYPT_COST_FACTOR = 12

# Password reset token expiry
PASSWORD_RESET_EXPIRY = timedelta(hours=1)

# Email verification token expiry
EMAIL_VERIFICATION_EXPIRY = timedelta(hours=24)


class AuthError(Exception):
    """Base authentication error."""


class InvalidCredentialsError(AuthError):
    """Raised when credentials are invalid."""


class AccountLockedError(AuthError):
    """Raised when account is locked due to rate limiting."""


class InvalidTokenError(AuthError):
    """Raised when a token is invalid or expired."""


class EmailAlreadyExistsError(AuthError):
    """Raised when registration email already exists."""


class MfaChallengeRequiredError(Exception):
    """Raised when MFA verification is needed to complete login."""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        super().__init__("MFA challenge required")


def hash_password(password: str) -> str:
    """Hash a password with bcrypt cost factor 12."""
    salt = bcrypt.gensalt(rounds=BCRYPT_COST_FACTOR)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )


class AuthService:
    """Orchestrates authentication flows.

    Coordinates between TokenService, SessionService, RateLimitService,
    and UserRepository to implement secure auth flows.
    """

    def __init__(
        self,
        user_repo: UserRepository,
        token_service: TokenService,
        session_service: SessionService,
        rate_limit_service: RateLimitService,
    ) -> None:
        self._user_repo = user_repo
        self._token_service = token_service
        self._session_service = session_service
        self._rate_limit_service = rate_limit_service

    async def register(
        self,
        email: str,
        password: str,
        display_name: str | None = None,
    ) -> dict[str, Any]:
        """Register a new user.

        Hashes password with bcrypt cost factor 12, creates user, issues tokens.

        Returns:
            Dict with access_token, refresh_token, and user info.

        Raises:
            EmailAlreadyExistsError: If email is already registered.
        """
        existing = await self._user_repo.find_by_email(email)
        if existing is not None:
            raise EmailAlreadyExistsError("Email already registered")

        password_hashed = hash_password(password)
        user = await self._user_repo.create(
            email=email,
            password_hash=password_hashed,
            display_name=display_name,
        )

        # Set email verification token
        verification_token = secrets.token_urlsafe(32)
        user.email_verification_token = verification_token
        user.email_verification_expires_at = (
            datetime.now(UTC) + EMAIL_VERIFICATION_EXPIRY
        )
        await self._user_repo.update(user)

        # Issue tokens
        tokens = self._issue_tokens(user)
        logger.info("User registered: user_id=%s", user.id)
        return tokens

    async def login(
        self,
        email: str,
        password: str,
    ) -> dict[str, Any]:
        """Authenticate a user with email and password.

        Checks rate limit, verifies credentials, handles MFA if enabled.

        Returns:
            Dict with access_token, refresh_token, and user info.

        Raises:
            AccountLockedError: If account is locked.
            InvalidCredentialsError: If credentials are wrong.
            MfaChallengeRequired: If MFA is enabled and needs verification.
        """
        # Check rate limit first
        if not self._rate_limit_service.check_login_rate_limit(email):
            logger.warning(
                "Login blocked by rate limit: email_hash=%s",
                hash(email),
            )
            raise AccountLockedError(
                "Account temporarily locked due to too many failed attempts"
            )

        user = await self._user_repo.find_by_email(email)
        if user is None:
            # Record failure even for unknown emails to prevent enumeration timing
            self._rate_limit_service.record_failed_attempt(email)
            raise InvalidCredentialsError("Invalid email or password")

        # Check if account is locked
        if user.locked_until is not None and user.locked_until > datetime.now(UTC):
            raise AccountLockedError(
                "Account temporarily locked due to too many failed attempts"
            )

        # Verify password
        if not verify_password(password, user.password_hash):
            self._rate_limit_service.record_failed_attempt(email)
            await self._user_repo.increment_failed_logins(user.id)

            # Check if we should lock the account
            if not self._rate_limit_service.check_login_rate_limit(email):
                lock_until = datetime.now(UTC) + timedelta(minutes=15)
                await self._user_repo.lock_account(user.id, lock_until)
                logger.warning(
                    "Account locked due to failed attempts: user_id=%s", user.id
                )

            raise InvalidCredentialsError("Invalid email or password")

        # Check MFA
        if user.mfa_enabled:
            raise MfaChallengeRequiredError(str(user.id))

        # Success: reset rate limit and issue tokens
        self._rate_limit_service.reset_on_success(email)
        await self._user_repo.reset_failed_logins(user.id)

        tokens = self._issue_tokens(user)
        logger.info("User logged in: user_id=%s", user.id)
        return tokens

    async def verify_email(self, token: str) -> bool:
        """Verify a user's email using the verification token.

        Returns:
            True if verification succeeded.

        Raises:
            InvalidTokenError: If token is invalid or expired.
        """
        # Find user by verification token
        user = await self._find_user_by_verification_token(token)
        if user is None:
            raise InvalidTokenError("Invalid or expired verification token")

        if (
            user.email_verification_expires_at is not None
            and user.email_verification_expires_at < datetime.now(UTC)
        ):
            raise InvalidTokenError("Verification token has expired")

        await self._user_repo.set_email_verified(user.id)
        logger.info("Email verified: user_id=%s", user.id)
        return True

    async def refresh_token(self, refresh_token: str, user_id: str) -> dict[str, Any]:
        """Rotate a refresh token.

        Validates the old refresh token, deletes it, and issues a new pair.
        Security: old token is deleted BEFORE new one is stored.

        Returns:
            Dict with new access_token and refresh_token.

        Raises:
            InvalidTokenError: If refresh token is not valid.
        """
        if not self._session_service.is_valid_session(user_id, refresh_token):
            raise InvalidTokenError("Invalid refresh token")

        # Security: delete old token BEFORE issuing new one
        self._session_service.revoke_session(user_id, refresh_token)

        user = await self._user_repo.find_by_id(uuid.UUID(user_id))
        if user is None:
            raise InvalidTokenError("User not found")

        # Issue new tokens
        new_refresh = self._token_service.create_refresh_token()
        self._session_service.create_session(user_id, new_refresh)

        org_id = str(user.organization_id) if user.organization_id else None
        roles = user.roles if isinstance(user.roles, list) else []
        access_token = self._token_service.create_access_token(
            user_id=str(user.id),
            org_id=org_id,
            roles=roles,
            mfa_enabled=user.mfa_enabled,
        )

        logger.info("Token refreshed for user_id=%s", user_id)
        return {
            "access_token": access_token,
            "refresh_token": new_refresh,
        }

    async def logout(self, user_id: str, refresh_token: str) -> bool:
        """Log out by revoking the refresh token session.

        Returns:
            True if logout succeeded.
        """
        self._session_service.revoke_session(user_id, refresh_token)
        logger.info("User logged out: user_id=%s", user_id)
        return True

    async def request_password_reset(self, email: str) -> None:
        """Request a password reset.

        Generates a token with 1h expiry and stores it on the user record.
        Silent success for unknown emails (prevents enumeration).
        """
        user = await self._user_repo.find_by_email(email)
        if user is None:
            # Silent success to prevent email enumeration
            return

        reset_token = secrets.token_urlsafe(32)
        user.password_reset_token = reset_token
        user.password_reset_expires_at = datetime.now(UTC) + PASSWORD_RESET_EXPIRY
        await self._user_repo.update(user)
        logger.info("Password reset requested: user_id=%s", user.id)

    async def confirm_password_reset(
        self, token: str, new_password: str
    ) -> bool:
        """Confirm a password reset with a new password.

        Validates token, hashes new password, invalidates all sessions.

        Returns:
            True if reset succeeded.

        Raises:
            InvalidTokenError: If token is invalid or expired.
        """
        user = await self._find_user_by_reset_token(token)
        if user is None:
            raise InvalidTokenError("Invalid or expired reset token")

        if user.password_reset_expires_at is not None:
            expires_at = user.password_reset_expires_at
            # Handle both timezone-aware and naive datetimes (SQLite returns naive)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at < datetime.now(UTC):
                raise InvalidTokenError("Reset token has expired")

        # Hash new password and clear reset token
        user.password_hash = hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_expires_at = None
        await self._user_repo.update(user)

        # Invalidate all sessions
        self._session_service.revoke_all_sessions(str(user.id))
        logger.info("Password reset confirmed: user_id=%s", user.id)
        return True

    async def issue_tokens_for_user(self, user_id: str) -> dict[str, Any]:
        """Look up a user by ID and issue tokens for them.

        Used after MFA verification to issue full tokens given only a user_id.

        Returns:
            Dict with access_token, refresh_token, and user info.

        Raises:
            InvalidTokenError: If the user is not found.
        """
        user = await self._user_repo.find_by_id(uuid.UUID(user_id))
        if user is None:
            raise InvalidTokenError("User not found")
        return self._issue_tokens(user)

    def _issue_tokens(self, user: User) -> dict[str, Any]:
        """Issue access and refresh tokens for a user."""
        org_id = str(user.organization_id) if user.organization_id else None
        roles = user.roles if isinstance(user.roles, list) else []

        access_token = self._token_service.create_access_token(
            user_id=str(user.id),
            org_id=org_id,
            roles=roles,
            mfa_enabled=user.mfa_enabled,
        )
        refresh_token = self._token_service.create_refresh_token()
        self._session_service.create_session(str(user.id), refresh_token)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_id": str(user.id),
            "email": user.email,
        }

    async def _find_user_by_verification_token(self, token: str) -> User | None:
        """Find a user by their email verification token.

        This is a simple lookup; in production, consider indexing this field.
        """
        from sqlalchemy import select

        from app.models.user import User as UserModel

        stmt = select(UserModel).where(
            UserModel.email_verification_token == token,
            UserModel.deleted_at.is_(None),
        )
        result = await self._user_repo._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_user_by_reset_token(self, token: str) -> User | None:
        """Find a user by their password reset token."""
        from sqlalchemy import select

        from app.models.user import User as UserModel

        stmt = select(UserModel).where(
            UserModel.password_reset_token == token,
            UserModel.deleted_at.is_(None),
        )
        result = await self._user_repo._session.execute(stmt)
        return result.scalar_one_or_none()
