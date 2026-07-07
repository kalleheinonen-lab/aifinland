"""Async SQLAlchemy engine and session factory."""

from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class DatabaseURLNotSetError(Exception):
    """Raised when DATABASE_URL environment variable is not set."""

    def __init__(self) -> None:
        super().__init__("DATABASE_URL environment variable is required but not set.")


def get_database_url() -> str:
    """Get DATABASE_URL from environment, raising if unset."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise DatabaseURLNotSetError()
    return url


def create_engine(database_url: str | None = None) -> AsyncEngine:
    """Create an async SQLAlchemy engine."""
    url = database_url or get_database_url()
    # Convert postgres:// to postgresql+asyncpg://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif not url.startswith("postgresql+asyncpg://"):
        url = f"postgresql+asyncpg://{url}"

    engine: AsyncEngine = create_async_engine(
        url,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
    )
    return engine


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory."""
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
