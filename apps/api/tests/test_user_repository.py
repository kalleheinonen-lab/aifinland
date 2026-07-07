"""Tests for UserRepository using in-memory SQLite async engine."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.models.user import Base, UserStatus
from app.repositories.user_repository import UserRepository


@pytest.fixture
async def async_session() -> AsyncSession:  # type: ignore[misc]
    """Create an in-memory SQLite async session for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Enable foreign keys for SQLite
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
def repo(async_session: AsyncSession) -> UserRepository:
    """Create a UserRepository with the test session."""
    return UserRepository(async_session)


class TestUserRepositoryCreate:
    """Tests for UserRepository.create method."""

    @pytest.mark.asyncio
    async def test_create_user_with_required_fields(
        self, repo: UserRepository, async_session: AsyncSession
    ) -> None:
        """AC-1: create() persists a user with email, password_hash, display_name."""
        user = await repo.create(
            email="test@example.com",
            password_hash="$2b$12$hashedpassword",
            display_name="Test User",
        )

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.password_hash == "$2b$12$hashedpassword"
        assert user.display_name == "Test User"
        assert user.status == UserStatus.ACTIVE.value
        assert user.email_verified is False
        assert user.failed_login_attempts == 0

    @pytest.mark.asyncio
    async def test_create_user_without_display_name(self, repo: UserRepository) -> None:
        """AC-1: create() works without display_name."""
        user = await repo.create(
            email="nodisplay@example.com",
            password_hash="$2b$12$hash",
        )

        assert user.display_name is None
        assert user.email == "nodisplay@example.com"

    @pytest.mark.asyncio
    async def test_create_user_generates_uuid(self, repo: UserRepository) -> None:
        """AC-1: create() generates a UUID primary key."""
        user = await repo.create(
            email="uuid@example.com",
            password_hash="$2b$12$hash",
        )

        assert isinstance(user.id, uuid.UUID)


class TestUserRepositoryFindByEmail:
    """Tests for UserRepository.find_by_email method."""

    @pytest.mark.asyncio
    async def test_find_by_email_existing_user(self, repo: UserRepository) -> None:
        """AC-2: find_by_email returns user when found."""
        created = await repo.create(
            email="find@example.com",
            password_hash="$2b$12$hash",
        )

        found = await repo.find_by_email("find@example.com")

        assert found is not None
        assert found.id == created.id
        assert found.email == "find@example.com"

    @pytest.mark.asyncio
    async def test_find_by_email_nonexistent(self, repo: UserRepository) -> None:
        """AC-2: find_by_email returns None when not found."""
        found = await repo.find_by_email("nonexistent@example.com")

        assert found is None

    @pytest.mark.asyncio
    async def test_find_by_email_excludes_soft_deleted(
        self, repo: UserRepository, async_session: AsyncSession
    ) -> None:
        """AC-2: find_by_email excludes soft-deleted users."""
        user = await repo.create(
            email="deleted@example.com",
            password_hash="$2b$12$hash",
        )
        user.deleted_at = datetime.now(UTC)
        await async_session.flush()

        found = await repo.find_by_email("deleted@example.com")

        assert found is None


class TestUserRepositoryFindById:
    """Tests for UserRepository.find_by_id method."""

    @pytest.mark.asyncio
    async def test_find_by_id_existing_user(self, repo: UserRepository) -> None:
        """AC-3: find_by_id returns user when found."""
        created = await repo.create(
            email="byid@example.com",
            password_hash="$2b$12$hash",
        )

        found = await repo.find_by_id(created.id)

        assert found is not None
        assert found.email == "byid@example.com"

    @pytest.mark.asyncio
    async def test_find_by_id_nonexistent(self, repo: UserRepository) -> None:
        """AC-3: find_by_id returns None for unknown ID."""
        found = await repo.find_by_id(uuid.uuid4())

        assert found is None

    @pytest.mark.asyncio
    async def test_find_by_id_excludes_soft_deleted(
        self, repo: UserRepository, async_session: AsyncSession
    ) -> None:
        """AC-3: find_by_id excludes soft-deleted users."""
        user = await repo.create(
            email="deleted2@example.com",
            password_hash="$2b$12$hash",
        )
        user.deleted_at = datetime.now(UTC)
        await async_session.flush()

        found = await repo.find_by_id(user.id)

        assert found is None


class TestUserRepositoryUpdate:
    """Tests for UserRepository.update method."""

    @pytest.mark.asyncio
    async def test_update_user_fields(
        self, repo: UserRepository, async_session: AsyncSession
    ) -> None:
        """AC-4: update() persists changes to user fields."""
        user = await repo.create(
            email="update@example.com",
            password_hash="$2b$12$hash",
            display_name="Original",
        )

        user.display_name = "Updated"
        updated = await repo.update(user)

        assert updated.display_name == "Updated"


class TestUserRepositoryIncrementFailedLogins:
    """Tests for UserRepository.increment_failed_logins method."""

    @pytest.mark.asyncio
    async def test_increment_failed_logins(
        self, repo: UserRepository, async_session: AsyncSession
    ) -> None:
        """AC-5: increment_failed_logins increases counter by 1."""
        user = await repo.create(
            email="fail@example.com",
            password_hash="$2b$12$hash",
        )
        assert user.failed_login_attempts == 0

        await repo.increment_failed_logins(user.id)
        await async_session.refresh(user)

        assert user.failed_login_attempts == 1

    @pytest.mark.asyncio
    async def test_increment_failed_logins_multiple(
        self, repo: UserRepository, async_session: AsyncSession
    ) -> None:
        """AC-5: increment_failed_logins accumulates."""
        user = await repo.create(
            email="fail2@example.com",
            password_hash="$2b$12$hash",
        )

        await repo.increment_failed_logins(user.id)
        await repo.increment_failed_logins(user.id)
        await repo.increment_failed_logins(user.id)
        await async_session.refresh(user)

        assert user.failed_login_attempts == 3


class TestUserRepositoryResetFailedLogins:
    """Tests for UserRepository.reset_failed_logins method."""

    @pytest.mark.asyncio
    async def test_reset_failed_logins(
        self, repo: UserRepository, async_session: AsyncSession
    ) -> None:
        """AC-6: reset_failed_logins sets counter to 0 and clears locked_until."""
        user = await repo.create(
            email="reset@example.com",
            password_hash="$2b$12$hash",
        )
        await repo.increment_failed_logins(user.id)
        await repo.lock_account(user.id, datetime.now(UTC) + timedelta(minutes=15))

        await repo.reset_failed_logins(user.id)
        await async_session.refresh(user)

        assert user.failed_login_attempts == 0
        assert user.locked_until is None


class TestUserRepositoryLockAccount:
    """Tests for UserRepository.lock_account method."""

    @pytest.mark.asyncio
    async def test_lock_account(
        self, repo: UserRepository, async_session: AsyncSession
    ) -> None:
        """AC-7: lock_account sets locked_until timestamp."""
        user = await repo.create(
            email="lock@example.com",
            password_hash="$2b$12$hash",
        )
        lock_time = datetime.now(UTC) + timedelta(minutes=15)

        await repo.lock_account(user.id, lock_time)
        await async_session.refresh(user)

        assert user.locked_until is not None


class TestUserRepositorySetEmailVerified:
    """Tests for UserRepository.set_email_verified method."""

    @pytest.mark.asyncio
    async def test_set_email_verified(
        self, repo: UserRepository, async_session: AsyncSession
    ) -> None:
        """AC-8: set_email_verified marks email as verified and clears token."""
        user = await repo.create(
            email="verify@example.com",
            password_hash="$2b$12$hash",
        )
        user.email_verification_token = "some-token"
        user.email_verification_expires_at = datetime.now(UTC) + timedelta(hours=24)
        await async_session.flush()

        await repo.set_email_verified(user.id)
        await async_session.refresh(user)

        assert user.email_verified is True
        assert user.email_verification_token is None
        assert user.email_verification_expires_at is None
