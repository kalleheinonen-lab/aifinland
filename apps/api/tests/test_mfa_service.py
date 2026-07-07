"""Tests for MFAService: TOTP setup, confirmation, verification, and backup codes.

# kills: wrong TOTP accepted, backup code reuse allowed, MFA enabled without
# confirmation, admin role bypasses MFA requirement, plaintext secret stored,
# TOTP replay accepted within the valid window.

Security invariants tested:
- Secrets are stored encrypted (Fernet), never in plaintext.
- Backup codes are stored as bcrypt hashes, never in plaintext.
- A backup code can only be used once.
- MFA is not enabled until the user confirms with a valid TOTP code.
- TOTP codes are single-use: replay within the valid window is rejected (RFC 6238 §5.2).
"""

import uuid
from typing import Any

import pyotp
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.models.user import Base
from app.repositories.user_repository import UserRepository
from app.services.mfa_service import (
    InvalidMFACodeError,
    MFAAlreadyEnabledError,
    MFANotSetupError,
    MFAService,
    _decrypt_secret,
    _encrypt_secret,
    _verify_backup_code,
)

# --- Test Fernet key (generated once for the test suite) ---
TEST_MFA_KEY = Fernet.generate_key().decode("utf-8")


# --- In-memory Valkey stub for tests ---


class FakeValkeyClient:
    """In-memory stub implementing the ValkeyClient protocol for tests."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def set(self, name: str, value: str, ex: int | None = None) -> Any:
        self._store[name] = value
        return True

    def get(self, name: str) -> Any:
        return self._store.get(name)

    def clear(self) -> None:
        """Reset all stored keys (used between tests)."""
        self._store.clear()


# --- Fixtures ---


@pytest.fixture(autouse=True)
def set_mfa_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set MFA_ENCRYPTION_KEY env var for all tests in this module."""
    monkeypatch.setenv("MFA_ENCRYPTION_KEY", TEST_MFA_KEY)


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
def fake_valkey() -> FakeValkeyClient:
    """Provide a fresh in-memory Valkey stub for each test."""
    return FakeValkeyClient()


@pytest.fixture
def mfa_service(user_repo: UserRepository, fake_valkey: FakeValkeyClient) -> MFAService:
    """Create an MFAService with the test repository and in-memory Valkey stub."""
    return MFAService(user_repo=user_repo, valkey_client=fake_valkey)


@pytest.fixture
async def test_user(user_repo: UserRepository):  # type: ignore[no-untyped-def]
    """Create a test user in the database."""
    return await user_repo.create(
        email="mfa_user@example.com",
        password_hash="$2b$12$fakehash",
        display_name="MFA Test User",
    )


# --- Encryption Helpers Tests ---


class TestEncryptionHelpers:
    """Tests for Fernet encryption helpers."""

    def test_encrypt_decrypt_roundtrip(self) -> None:
        """Encrypting then decrypting a secret returns the original value."""
        original = "JBSWY3DPEHPK3PXP"
        encrypted = _encrypt_secret(original)
        # AC: encrypted form must not equal plaintext
        assert encrypted != original
        # AC: decryption recovers the original
        assert _decrypt_secret(encrypted) == original

    def test_encrypted_secret_is_not_plaintext(self) -> None:
        """The stored secret must not contain the plaintext TOTP seed."""
        secret = "JBSWY3DPEHPK3PXP"
        encrypted = _encrypt_secret(secret)
        assert secret not in encrypted


# --- MFA Setup Tests ---


class TestMFASetup:
    """Tests for setup_mfa()."""

    @pytest.mark.asyncio
    async def test_ac1_setup_generates_valid_provisioning_uri(
        self, mfa_service: MFAService, test_user
    ) -> None:
        """AC-1: setup_mfa returns a provisioning URI containing issuer and email."""
        result = await mfa_service.setup_mfa(str(test_user.id))

        # AC-1: provisioning URI must be a valid otpauth:// URI
        uri = result["provisioning_uri"]
        assert isinstance(uri, str)
        assert uri.startswith("otpauth://totp/")
        assert "AI%20Finland" in uri or "AI Finland" in uri
        assert "mfa_user%40example.com" in uri or "mfa_user@example.com" in uri

    @pytest.mark.asyncio
    async def test_setup_returns_secret_and_backup_codes(
        self, mfa_service: MFAService, test_user
    ) -> None:
        """setup_mfa returns a secret and 10 backup codes."""
        result = await mfa_service.setup_mfa(str(test_user.id))

        assert "secret" in result
        assert "backup_codes" in result
        # AC: exactly 10 backup codes
        assert len(result["backup_codes"]) == 10  # type: ignore[arg-type]
        # AC: each backup code is 8 alphanumeric characters
        for code in result["backup_codes"]:  # type: ignore[union-attr]
            assert len(code) == 8
            assert code.isalnum()

    @pytest.mark.asyncio
    async def test_setup_does_not_enable_mfa(
        self, mfa_service: MFAService, test_user, user_repo: UserRepository
    ) -> None:
        """setup_mfa stores the secret but does NOT enable MFA."""
        await mfa_service.setup_mfa(str(test_user.id))

        # Reload user from DB
        user = await user_repo.find_by_id(test_user.id)
        assert user is not None
        # AC: mfa_enabled must still be False after setup
        assert user.mfa_enabled is False
        # AC: secret must be stored (encrypted)
        assert user.mfa_secret is not None

    @pytest.mark.asyncio
    async def test_setup_stores_encrypted_secret(
        self, mfa_service: MFAService, test_user, user_repo: UserRepository
    ) -> None:
        """The stored secret must be encrypted, not the raw TOTP seed."""
        result = await mfa_service.setup_mfa(str(test_user.id))
        plaintext_secret = result["secret"]

        user = await user_repo.find_by_id(test_user.id)
        assert user is not None
        # AC: stored value must not equal the plaintext secret
        assert user.mfa_secret != plaintext_secret
        # AC: decrypting the stored value must recover the plaintext secret
        assert _decrypt_secret(user.mfa_secret) == plaintext_secret  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_setup_stores_hashed_backup_codes(
        self, mfa_service: MFAService, test_user, user_repo: UserRepository
    ) -> None:
        """Backup codes are stored as bcrypt hashes, not plaintext."""
        result = await mfa_service.setup_mfa(str(test_user.id))
        plaintext_codes = result["backup_codes"]

        user = await user_repo.find_by_id(test_user.id)
        assert user is not None
        stored_codes: list[str] = user.mfa_backup_codes  # type: ignore[assignment]
        assert len(stored_codes) == 10

        # AC: each stored code must be a bcrypt hash (starts with $2b$)
        for hashed in stored_codes:
            assert hashed.startswith("$2b$12$")

        # AC: each plaintext code must verify against its stored hash
        for plaintext, hashed in zip(plaintext_codes, stored_codes):  # type: ignore[arg-type]
            assert _verify_backup_code(plaintext, hashed)

    @pytest.mark.asyncio
    async def test_setup_raises_if_mfa_already_enabled(
        self, mfa_service: MFAService, test_user, user_repo: UserRepository
    ) -> None:
        """setup_mfa raises MFAAlreadyEnabledError if MFA is already active."""
        # Manually enable MFA
        test_user.mfa_enabled = True
        await user_repo.update(test_user)

        with pytest.raises(MFAAlreadyEnabledError):
            await mfa_service.setup_mfa(str(test_user.id))


# --- MFA Confirmation Tests ---


class TestMFAConfirmation:
    """Tests for confirm_mfa_setup()."""

    @pytest.mark.asyncio
    async def test_ac2_confirm_with_correct_code_enables_mfa(
        self, mfa_service: MFAService, test_user, user_repo: UserRepository
    ) -> None:
        """AC-2: confirm_mfa_setup with a valid TOTP code sets mfa_enabled=True."""
        result = await mfa_service.setup_mfa(str(test_user.id))
        secret = result["secret"]

        # Generate a valid TOTP code
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        # AC-2: expect True returned and mfa_enabled set
        success = await mfa_service.confirm_mfa_setup(str(test_user.id), valid_code)
        assert success is True

        user = await user_repo.find_by_id(test_user.id)
        assert user is not None
        assert user.mfa_enabled is True

    @pytest.mark.asyncio
    async def test_ac3_confirm_with_wrong_code_does_not_enable_mfa(
        self, mfa_service: MFAService, test_user, user_repo: UserRepository
    ) -> None:
        """AC-3: confirm_mfa_setup with invalid code raises and does not enable MFA."""
        await mfa_service.setup_mfa(str(test_user.id))

        # AC-3: expect InvalidMFACodeError, mfa_enabled stays False
        with pytest.raises(InvalidMFACodeError):
            await mfa_service.confirm_mfa_setup(str(test_user.id), "000000")

        user = await user_repo.find_by_id(test_user.id)
        assert user is not None
        assert user.mfa_enabled is False

    @pytest.mark.asyncio
    async def test_confirm_raises_if_no_secret(
        self, mfa_service: MFAService, test_user
    ) -> None:
        """confirm_mfa_setup raises MFANotSetupError if setup was never called."""
        with pytest.raises(MFANotSetupError):
            await mfa_service.confirm_mfa_setup(str(test_user.id), "123456")


# --- MFA Verification Tests ---


class TestMFAVerification:
    """Tests for verify_mfa()."""

    @pytest.fixture
    async def mfa_enabled_user(
        self, mfa_service: MFAService, test_user, user_repo: UserRepository
    ):  # type: ignore[no-untyped-def]
        """Set up and confirm MFA for the test user.

        Returns (user, secret, backup_codes).
        """
        result = await mfa_service.setup_mfa(str(test_user.id))
        secret = result["secret"]
        backup_codes = result["backup_codes"]

        totp = pyotp.TOTP(secret)
        await mfa_service.confirm_mfa_setup(str(test_user.id), totp.now())

        return test_user, secret, backup_codes

    @pytest.mark.asyncio
    async def test_ac4_verify_with_valid_totp_returns_true(
        self, mfa_service: MFAService, mfa_enabled_user
    ) -> None:
        """AC-4: verify_mfa with a valid TOTP code returns True."""
        user, secret, _ = mfa_enabled_user
        totp = pyotp.TOTP(secret)

        # AC-4: expect True for a valid TOTP code
        result = await mfa_service.verify_mfa(str(user.id), totp.now())
        assert result is True

    @pytest.mark.asyncio
    async def test_ac5_verify_with_invalid_totp_returns_false(
        self, mfa_service: MFAService, mfa_enabled_user
    ) -> None:
        """AC-5: verify_mfa with an invalid TOTP code returns False."""
        user, _, _ = mfa_enabled_user

        # AC-5: expect False for a clearly wrong code
        result = await mfa_service.verify_mfa(str(user.id), "000000")
        assert result is False

    @pytest.mark.asyncio
    async def test_ac6_verify_with_valid_backup_code_returns_true_and_marks_used(
        self, mfa_service: MFAService, mfa_enabled_user, user_repo: UserRepository
    ) -> None:
        """AC-6: verify_mfa with a valid backup code returns True and removes it."""
        user, _, backup_codes = mfa_enabled_user
        first_code = backup_codes[0]

        # AC-6: expect True and code consumed
        result = await mfa_service.verify_mfa(str(user.id), first_code)
        assert result is True

        # Verify the code was removed from the stored list
        refreshed = await user_repo.find_by_id(user.id)
        assert refreshed is not None
        remaining: list[str] = refreshed.mfa_backup_codes  # type: ignore[assignment]
        # AC-6: 9 codes remain after consuming one
        assert len(remaining) == 9

    @pytest.mark.asyncio
    async def test_ac7_backup_code_cannot_be_reused(
        self, mfa_service: MFAService, mfa_enabled_user
    ) -> None:
        """AC-7: A backup code that has been used cannot be used again."""
        user, _, backup_codes = mfa_enabled_user
        first_code = backup_codes[0]

        # First use: should succeed
        first_result = await mfa_service.verify_mfa(str(user.id), first_code)
        assert first_result is True

        # Second use: same code must fail
        # AC-7: expect False on reuse
        second_result = await mfa_service.verify_mfa(str(user.id), first_code)
        assert second_result is False

    @pytest.mark.asyncio
    async def test_verify_returns_false_for_unknown_user(
        self, mfa_service: MFAService
    ) -> None:
        """verify_mfa returns False (not an error) for a non-existent user."""
        result = await mfa_service.verify_mfa(str(uuid.uuid4()), "123456")
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_returns_false_when_no_secret(
        self, mfa_service: MFAService, test_user
    ) -> None:
        """verify_mfa returns False when no MFA secret is stored."""
        result = await mfa_service.verify_mfa(str(test_user.id), "123456")
        assert result is False

    @pytest.mark.asyncio
    async def test_ac_replay_same_totp_code_rejected_on_second_use(
        self,
        mfa_service: MFAService,
        mfa_enabled_user,
        fake_valkey: FakeValkeyClient,
    ) -> None:
        """AC-replay: A valid TOTP code cannot be used twice within the valid window.

        RFC 6238 §5.2 requires each OTP be used at most once.
        # kills: replay check missing, timecode not stored, TTL too short
        """
        user, secret, _ = mfa_enabled_user
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        # First use: expect True
        first_result = await mfa_service.verify_mfa(str(user.id), valid_code)
        # AC-replay: first use of a valid TOTP code must succeed
        assert first_result is True

        # Second use of the same code within the same window: expect False (replay)
        second_result = await mfa_service.verify_mfa(str(user.id), valid_code)
        # AC-replay: replay of the same TOTP code must be rejected
        assert second_result is False

    @pytest.mark.asyncio
    async def test_ac_replay_different_user_same_code_not_blocked(
        self,
        user_repo: UserRepository,
        fake_valkey: FakeValkeyClient,
    ) -> None:
        """AC-replay: Replay protection is per-user.

        The same code used by user A must not block user B.
        # kills: global key without user_id, cross-user replay false positive
        """
        # Create two users with the SAME TOTP secret (edge case)
        user_a = await user_repo.create(
            email="replay_user_a@example.com",
            password_hash="$2b$12$fakehash",
            display_name="Replay User A",
        )
        user_b = await user_repo.create(
            email="replay_user_b@example.com",
            password_hash="$2b$12$fakehash",
            display_name="Replay User B",
        )

        secret = pyotp.random_base32()
        from app.services.mfa_service import _encrypt_secret

        encrypted = _encrypt_secret(secret)
        user_a.mfa_secret = encrypted
        user_a.mfa_enabled = True
        user_b.mfa_secret = encrypted
        user_b.mfa_enabled = True
        await user_repo.update(user_a)
        await user_repo.update(user_b)

        svc = MFAService(user_repo=user_repo, valkey_client=fake_valkey)
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        # User A uses the code first
        result_a = await svc.verify_mfa(str(user_a.id), valid_code)
        # AC-replay: user A's first use must succeed
        assert result_a is True

        # User B uses the same code: must NOT be blocked (different user)
        result_b = await svc.verify_mfa(str(user_b.id), valid_code)
        # AC-replay: user B is a different user; same code must be accepted
        assert result_b is True

    @pytest.mark.asyncio
    async def test_ac_replay_totp_accepted_after_cache_cleared(
        self,
        mfa_service: MFAService,
        mfa_enabled_user,
        fake_valkey: FakeValkeyClient,
    ) -> None:
        """AC-replay: After the Valkey TTL expires (simulated by clearing cache),
        a new code from the same window is accepted again.

        This verifies the TTL-based expiry path: once the cache entry is gone,
        the timecode is no longer considered used.
        # kills: permanent blocking instead of TTL-based expiry
        """
        user, secret, _ = mfa_enabled_user
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        # First use succeeds
        first_result = await mfa_service.verify_mfa(str(user.id), valid_code)
        assert first_result is True

        # Simulate TTL expiry by clearing the Valkey store
        fake_valkey.clear()

        # After expiry, the same code (same timecode) is accepted again
        # (in production this would only happen after 90s when the window has passed)
        after_expiry_result = await mfa_service.verify_mfa(str(user.id), valid_code)
        # AC-replay: after cache expiry, the timecode is no longer blocked
        assert after_expiry_result is True


# --- Role-Based MFA Requirement Tests ---


class TestMFARequirement:
    """Tests for is_mfa_required() and is_mfa_setup_complete()."""

    def test_ac8_is_mfa_required_true_for_admin(
        self, mfa_service: MFAService
    ) -> None:
        """AC-8: is_mfa_required returns True for 'admin' role."""
        # AC-8: admin role must require MFA
        assert mfa_service.is_mfa_required(["admin"]) is True

    def test_ac8_is_mfa_required_true_for_super_admin(
        self, mfa_service: MFAService
    ) -> None:
        """AC-8: is_mfa_required returns True for 'super_admin' role."""
        # AC-8: super_admin role must require MFA
        assert mfa_service.is_mfa_required(["super_admin"]) is True

    def test_is_mfa_required_true_for_mixed_roles_with_admin(
        self, mfa_service: MFAService
    ) -> None:
        """is_mfa_required returns True when admin is among multiple roles."""
        assert mfa_service.is_mfa_required(["user", "admin"]) is True

    def test_is_mfa_required_false_for_regular_user(
        self, mfa_service: MFAService
    ) -> None:
        """is_mfa_required returns False for non-privileged roles."""
        assert mfa_service.is_mfa_required(["user"]) is False

    def test_is_mfa_required_false_for_empty_roles(
        self, mfa_service: MFAService
    ) -> None:
        """is_mfa_required returns False for empty role list."""
        assert mfa_service.is_mfa_required([]) is False

    @pytest.mark.asyncio
    async def test_is_mfa_setup_complete_true_when_enabled(
        self, mfa_service: MFAService, test_user, user_repo: UserRepository
    ) -> None:
        """is_mfa_setup_complete returns True when mfa_enabled is True."""
        test_user.mfa_enabled = True
        await user_repo.update(test_user)

        assert mfa_service.is_mfa_setup_complete(test_user) is True

    @pytest.mark.asyncio
    async def test_is_mfa_setup_complete_false_when_not_enabled(
        self, mfa_service: MFAService, test_user
    ) -> None:
        """is_mfa_setup_complete returns False when mfa_enabled is False."""
        assert mfa_service.is_mfa_setup_complete(test_user) is False
