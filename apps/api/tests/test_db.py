"""Tests for the database module."""

import pytest

from app.db import DatabaseURLNotSetError, create_engine, get_database_url


class TestGetDatabaseUrl:
    """Tests for get_database_url function."""

    def test_raises_when_database_url_not_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-9: Throws named error if DATABASE_URL is unset."""
        monkeypatch.delenv("DATABASE_URL", raising=False)

        with pytest.raises(DatabaseURLNotSetError):
            get_database_url()

    def test_returns_url_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AC-9: Returns DATABASE_URL when set."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/testdb")

        url = get_database_url()

        assert url == "postgresql://localhost/testdb"


class TestCreateEngine:
    """Tests for create_engine function."""

    def test_converts_postgres_scheme(self) -> None:
        """AC-10: Converts postgres:// to postgresql+asyncpg://."""
        engine = create_engine("postgres://user:pass@localhost/db")

        assert "postgresql+asyncpg://" in str(engine.url)

    def test_converts_postgresql_scheme(self) -> None:
        """AC-10: Converts postgresql:// to postgresql+asyncpg://."""
        engine = create_engine("postgresql://user:pass@localhost/db")

        assert "postgresql+asyncpg://" in str(engine.url)

    def test_keeps_asyncpg_scheme(self) -> None:
        """AC-10: Keeps postgresql+asyncpg:// as-is."""
        engine = create_engine("postgresql+asyncpg://user:pass@localhost/db")

        assert "postgresql+asyncpg://" in str(engine.url)
