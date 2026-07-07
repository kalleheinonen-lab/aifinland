"""Database session configuration for async PostgreSQL access."""

from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def _get_database_url() -> str:
    """Read DATABASE_URL from environment, raising if not set."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Set it to a PostgreSQL connection string "
            "(e.g. postgresql+asyncpg://user:pass@host/db)."
        )
    return url


def get_async_engine() -> AsyncEngine:
    """Create and return an async SQLAlchemy engine.

    Reads DATABASE_URL from the environment. Raises RuntimeError if not set.
    """
    url = _get_database_url()
    return create_async_engine(
        url,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
    )


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create an async session factory bound to the default engine."""
    engine = get_async_engine()
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


# Convenience alias matching the naming convention used by consumers.
AsyncSessionLocal = get_async_session_factory
