"""User repository for database operations."""

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserStatus


class UserRepository:
    """Repository for User CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        email: str,
        password_hash: str,
        display_name: str | None = None,
    ) -> User:
        """Create a new user."""
        user = User(
            id=uuid.uuid4(),
            email=email,
            password_hash=password_hash,
            display_name=display_name,
            status=UserStatus.ACTIVE.value,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def find_by_email(self, email: str) -> User | None:
        """Find a user by email address."""
        stmt = select(User).where(
            User.email == email,
            User.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_id(self, user_id: uuid.UUID) -> User | None:
        """Find a user by ID."""
        stmt = select(User).where(
            User.id == user_id,
            User.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, user: User) -> User:
        """Update an existing user (flush pending changes)."""
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def increment_failed_logins(self, user_id: uuid.UUID) -> None:
        """Increment the failed login attempts counter."""
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                failed_login_attempts=User.failed_login_attempts + 1,
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def reset_failed_logins(self, user_id: uuid.UUID) -> None:
        """Reset failed login attempts to zero."""
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                failed_login_attempts=0,
                locked_until=None,
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def lock_account(self, user_id: uuid.UUID, until: datetime) -> None:
        """Lock a user account until the specified time."""
        stmt = update(User).where(User.id == user_id).values(locked_until=until)
        await self._session.execute(stmt)
        await self._session.flush()

    async def set_email_verified(self, user_id: uuid.UUID) -> None:
        """Mark a user's email as verified."""
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                email_verified=True,
                email_verification_token=None,
                email_verification_expires_at=None,
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()
