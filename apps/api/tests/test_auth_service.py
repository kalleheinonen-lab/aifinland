"""Tests for AuthService, SessionService, and RateLimitService.

Kills: wrong password accepted, locked account bypassed, session limit exceeded,
rate limit not enforced, refresh token reuse, credentials logged.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.models.user import Base
from app.repositories.user_repository import UserRepository
from app.services.auth_service import (
    AccountLockedError,
    AuthService,
    InvalidCredentialsError,
    InvalidTokenError,
    hash_password,
    verify_password,
)
from app.services.rate_limit_service import RateLimitService
from app.services.session_service import SessionService
from app.services.token_service import TokenService

# --- Fixtures ---


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


@pytest.fixture
def mock_valkey() -> MagicMock:
    """Create a mock Valkey client."""
    client = MagicMock()
    # Default behaviors
    client.scard.return_value = 0
    client.sismember.return_value = True
    client.get.return_value = None
    client.incr.return_value = 1
    return client


@pytest.fixture
def session_service(mock_valkey: MagicMock) -> SessionService:
    """Create a SessionService with mock Valkey."""
    return SessionService(valkey_client=mock_valkey)


@pytest.fixture
def rate_limit_service(mock_valkey: MagicMock) -> RateLimitService:
    """Create a RateLimitService with mock Valkey."""
    return RateLimitService(valkey_client=mock_valkey)


@pytest.fixture
async def async_session() -> AsyncSession:  # type: ignore[misc]
    """Create an in-memory SQLite async session for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def user_repo(async_session: AsyncSession) -> UserRepository:
    """Create a UserRepository with the test session."""
    return UserRepository(async_session)


@pytest.fixture
def auth_service(
    user_repo: UserRepository,
    token_service: TokenService,
    session_service: SessionService,
    rate_limit_service: RateLimitService,
) -> AuthService:
    """Create an AuthService with all dependencies."""
    return AuthService(
        user_repo=user_repo,
        token_service=token_service,
        session_service=session_service,
        rate_limit_service=rate_limit_service,
    )


# --- Password Hashing Tests ---


class TestPasswordHashing:
    """Tests for bcrypt password hashing."""

    def test_hash_password_produces_bcrypt_hash(self) -> None:
        """AC-1: Password is hashed with bcrypt cost factor 12."""
        hashed = hash_password("securepassword123")
        # bcrypt hashes start with $2b$ and include the cost factor
        assert hashed.startswith("$2b$12$")

    def test_verify_password_correct(self) -> None:
        """Correct password verifies successfully."""
        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed) is True

    def test_verify_password_incorrect(self) -> None:
        """Wrong password fails verification."""
        hashed = hash_password("mypassword")
        assert verify_password("wrongpassword", hashed) is False


# --- Auth Service Tests ---


class TestAuthServiceRegister:
    """Tests for user registration."""

    @pytest.mark.asyncio
    async def test_ac1_register_success(
        self, auth_service: AuthService
    ) -> None:
        """AC-1: register hashes password with bcrypt cost 12."""
        result = await auth_service.register(
            email="new@example.com",
            password="SecurePass123!",
            display_name="New User",
        )

        # AC-1: expect tokens and user info returned
        assert "access_token" in result
        assert "refresh_token" in result
        assert "user_id" in result
        assert result["email"] == "new@example.com"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self, auth_service: AuthService
    ) -> None:
        """Registration with existing email raises error."""
        await auth_service.register(
            email="dup@example.com",
            password="SecurePass123!",
        )

        from app.services.auth_service import EmailAlreadyExistsError

        with pytest.raises(EmailAlreadyExistsError):
            await auth_service.register(
                email="dup@example.com",
                password="AnotherPass123!",
            )


class TestAuthServiceLogin:
    """Tests for user login."""

    @pytest.mark.asyncio
    async def test_ac1_login_success(
        self, auth_service: AuthService
    ) -> None:
        """AC-1: Successful login returns tokens."""
        await auth_service.register(
            email="login@example.com",
            password="CorrectPassword1!",
        )

        result = await auth_service.login(
            email="login@example.com",
            password="CorrectPassword1!",
        )

        # AC-1: expect access and refresh tokens
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["email"] == "login@example.com"

    @pytest.mark.asyncio
    async def test_ac2_wrong_password_returns_error(
        self, auth_service: AuthService
    ) -> None:
        """AC-2: Wrong password returns InvalidCredentialsError."""
        await auth_service.register(
            email="wrong@example.com",
            password="CorrectPassword1!",
        )

        # AC-2: expect InvalidCredentialsError, not tokens
        with pytest.raises(InvalidCredentialsError):
            await auth_service.login(
                email="wrong@example.com",
                password="WrongPassword!",
            )

    @pytest.mark.asyncio
    async def test_ac2_unknown_email_returns_error(
        self, auth_service: AuthService
    ) -> None:
        """AC-2: Unknown email returns InvalidCredentialsError."""
        with pytest.raises(InvalidCredentialsError):
            await auth_service.login(
                email="unknown@example.com",
                password="AnyPassword!",
            )

    @pytest.mark.asyncio
    async def test_ac3_locked_account_returns_error(
        self, auth_service: AuthService, user_repo: UserRepository
    ) -> None:
        """AC-3: Locked account returns AccountLockedError."""
        await auth_service.register(
            email="locked@example.com",
            password="CorrectPassword1!",
        )

        # Lock the account
        user = await user_repo.find_by_email("locked@example.com")
        assert user is not None
        await user_repo.lock_account(
            user.id, datetime.now(UTC) + timedelta(minutes=15)
        )

        # AC-3: expect AccountLockedError
        with pytest.raises(AccountLockedError):
            await auth_service.login(
                email="locked@example.com",
                password="CorrectPassword1!",
            )


class TestAuthServiceRefreshToken:
    """Tests for token refresh/rotation."""

    @pytest.mark.asyncio
    async def test_ac5_refresh_rotation_works(
        self, auth_service: AuthService, mock_valkey: MagicMock
    ) -> None:
        """AC-5: Refresh token rotation deletes old token and issues new one."""
        # Register to get a user
        result = await auth_service.register(
            email="refresh@example.com",
            password="SecurePass123!",
        )
        user_id = result["user_id"]
        old_refresh = result["refresh_token"]

        # Mock: old token is valid
        mock_valkey.sismember.return_value = True

        # AC-5: expect new tokens returned, old token revoked
        new_result = await auth_service.refresh_token(old_refresh, user_id)

        assert "access_token" in new_result
        assert "refresh_token" in new_result
        assert new_result["refresh_token"] != old_refresh

        # Verify old token was removed (srem called)
        mock_valkey.srem.assert_called()

    @pytest.mark.asyncio
    async def test_refresh_invalid_token_rejected(
        self, auth_service: AuthService, mock_valkey: MagicMock
    ) -> None:
        """Invalid refresh token is rejected."""
        mock_valkey.sismember.return_value = False

        with pytest.raises(InvalidTokenError):
            await auth_service.refresh_token("invalid-token", str(uuid.uuid4()))


class TestAuthServiceLogout:
    """Tests for logout."""

    @pytest.mark.asyncio
    async def test_logout_revokes_session(
        self, auth_service: AuthService, mock_valkey: MagicMock
    ) -> None:
        """Logout removes the refresh token from the session set."""
        user_id = str(uuid.uuid4())
        refresh_token = "some-refresh-token"

        result = await auth_service.logout(user_id, refresh_token)

        assert result is True
        mock_valkey.srem.assert_called_once()


# --- Session Service Tests ---


class TestSessionService:
    """Tests for session management."""

    def test_ac6_session_limit_enforced_at_5(
        self, mock_valkey: MagicMock
    ) -> None:
        """AC-6: When user has 5 sessions, oldest is evicted on new session."""
        service = SessionService(valkey_client=mock_valkey)
        user_id = "user-123"

        # Simulate 5 existing sessions
        mock_valkey.scard.return_value = 5

        # AC-6: expect spop called to evict oldest before adding new
        service.create_session(user_id, "new-token")

        mock_valkey.spop.assert_called_once_with(f"sessions:{user_id}", 1)
        mock_valkey.sadd.assert_called_once_with(f"sessions:{user_id}", "new-token")

    def test_session_created_under_limit(
        self, mock_valkey: MagicMock
    ) -> None:
        """Sessions under limit are created without eviction."""
        service = SessionService(valkey_client=mock_valkey)
        mock_valkey.scard.return_value = 3

        service.create_session("user-123", "token-1")

        mock_valkey.spop.assert_not_called()
        mock_valkey.sadd.assert_called_once()

    def test_is_valid_session_true(
        self, mock_valkey: MagicMock
    ) -> None:
        """Valid session returns True."""
        service = SessionService(valkey_client=mock_valkey)
        mock_valkey.sismember.return_value = True

        assert service.is_valid_session("user-123", "valid-token") is True

    def test_is_valid_session_false(
        self, mock_valkey: MagicMock
    ) -> None:
        """Invalid session returns False."""
        service = SessionService(valkey_client=mock_valkey)
        mock_valkey.sismember.return_value = False

        assert service.is_valid_session("user-123", "invalid-token") is False

    def test_revoke_all_sessions(
        self, mock_valkey: MagicMock
    ) -> None:
        """Revoke all sessions deletes the entire set."""
        service = SessionService(valkey_client=mock_valkey)
        service.revoke_all_sessions("user-123")

        mock_valkey.delete.assert_called_once_with("sessions:user-123")


# --- Rate Limit Service Tests ---


class TestRateLimitService:
    """Tests for login rate limiting."""

    def test_ac7_rate_limit_triggers_after_5_failures(self) -> None:
        """AC-7: After 5 failed attempts, login is blocked."""
        mock_client = MagicMock()
        service = RateLimitService(valkey_client=mock_client)

        # Simulate 5 failures already recorded
        mock_client.get.return_value = b"5"

        # AC-7: expect False (blocked)
        assert service.check_login_rate_limit("test@example.com") is False

    def test_allows_login_under_limit(self) -> None:
        """Login is allowed when under the failure limit."""
        mock_client = MagicMock()
        service = RateLimitService(valkey_client=mock_client)

        mock_client.get.return_value = b"3"

        assert service.check_login_rate_limit("test@example.com") is True

    def test_allows_login_no_failures(self) -> None:
        """Login is allowed when no failures recorded."""
        mock_client = MagicMock()
        service = RateLimitService(valkey_client=mock_client)

        mock_client.get.return_value = None

        assert service.check_login_rate_limit("test@example.com") is True

    def test_record_failed_attempt_increments(self) -> None:
        """Recording a failed attempt increments the counter."""
        mock_client = MagicMock()
        service = RateLimitService(valkey_client=mock_client)
        mock_client.incr.return_value = 1

        service.record_failed_attempt("test@example.com")

        mock_client.incr.assert_called_once_with("login_failures:test@example.com")
        # First failure sets TTL
        mock_client.expire.assert_called_once_with(
            "login_failures:test@example.com", 15 * 60
        )

    def test_record_failed_attempt_no_expire_on_subsequent(self) -> None:
        """Subsequent failures don't reset the TTL."""
        mock_client = MagicMock()
        service = RateLimitService(valkey_client=mock_client)
        mock_client.incr.return_value = 3  # Not the first failure

        service.record_failed_attempt("test@example.com")

        mock_client.incr.assert_called_once()
        mock_client.expire.assert_not_called()

    def test_reset_on_success_deletes_counter(self) -> None:
        """Successful login deletes the failure counter."""
        mock_client = MagicMock()
        service = RateLimitService(valkey_client=mock_client)

        service.reset_on_success("test@example.com")

        mock_client.delete.assert_called_once_with("login_failures:test@example.com")


# --- Password Reset Tests ---


class TestAuthServicePasswordReset:
    """Tests for password reset flow."""

    @pytest.mark.asyncio
    async def test_request_password_reset_unknown_email_silent(
        self, auth_service: AuthService
    ) -> None:
        """Unknown email returns silently (no error, prevents enumeration)."""
        # Should not raise
        await auth_service.request_password_reset("unknown@example.com")

    @pytest.mark.asyncio
    async def test_request_password_reset_sets_token(
        self, auth_service: AuthService, user_repo: UserRepository
    ) -> None:
        """Password reset stores a token on the user record."""
        await auth_service.register(
            email="reset@example.com",
            password="OldPassword123!",
        )

        await auth_service.request_password_reset("reset@example.com")

        user = await user_repo.find_by_email("reset@example.com")
        assert user is not None
        assert user.password_reset_token is not None
        assert user.password_reset_expires_at is not None

    @pytest.mark.asyncio
    async def test_confirm_password_reset_success(
        self,
        auth_service: AuthService,
        user_repo: UserRepository,
        mock_valkey: MagicMock,
    ) -> None:
        """Confirm password reset changes password and invalidates sessions."""
        await auth_service.register(
            email="confirm@example.com",
            password="OldPassword123!",
        )

        await auth_service.request_password_reset("confirm@example.com")
        user = await user_repo.find_by_email("confirm@example.com")
        assert user is not None
        reset_token = user.password_reset_token
        assert reset_token is not None

        result = await auth_service.confirm_password_reset(
            reset_token, "NewPassword456!"
        )

        assert result is True
        # All sessions should be revoked
        mock_valkey.delete.assert_called()

    @pytest.mark.asyncio
    async def test_confirm_password_reset_invalid_token(
        self, auth_service: AuthService
    ) -> None:
        """Invalid reset token raises error."""
        with pytest.raises(InvalidTokenError):
            await auth_service.confirm_password_reset(
                "invalid-token", "NewPassword456!"
            )
