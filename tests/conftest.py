"""Shared test fixtures for model inspection and migration parsing."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import MetaData

_VERSIONS_DIR = Path(__file__).resolve().parent.parent / "alembic" / "versions"


@pytest.fixture(scope="session")
def db_metadata() -> MetaData:
    """Provide Base.metadata with all models registered (session-scoped)."""
    import app.db.models  # noqa: F401  (side-effect: populates Base.metadata)
    from app.db.base import Base

    return Base.metadata


@pytest.fixture(scope="session")
def all_migration_text() -> str:
    """Concatenated text of all migration files for SQL parsing tests."""
    parts: list[str] = []
    for migration_file in sorted(_VERSIONS_DIR.glob("*.py")):
        parts.append(migration_file.read_text(encoding="utf-8"))
    return "\n".join(parts)


@pytest.fixture(scope="session")
def seed_migration_text() -> str:
    """Text of the seed migration (0002) for seed data contract tests."""
    seed_file = _VERSIONS_DIR / "0002_seed_admin_data.py"
    return seed_file.read_text(encoding="utf-8")
