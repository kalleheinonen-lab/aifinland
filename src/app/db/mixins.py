"""Shared column mixins for SQLAlchemy 2.0 declarative models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.types import VisibilityType, uuid7


class EntityMetadataMixin:
    """Mixin that adds standard audit/metadata columns to a model.

    All Python attribute names use snake_case matching the database column
    names exactly. This is required for the RLS CI gate which inspects
    __table__.columns to verify 'organization_id' is present.

    Models that inherit this mixin MUST also inherit from Base (or a
    subclass of DeclarativeBase). Organization does NOT inherit this mixin
    because it would create a self-referential FK loop.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid7,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
        default=None,
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", use_alter=True, name="fk_%(table_name)s_created_by_user"),
        nullable=True,
        default=None,
    )

    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", use_alter=True, name="fk_%(table_name)s_updated_by_user"),
        nullable=True,
        default=None,
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", use_alter=True, name="fk_%(table_name)s_organization"),
        nullable=True,
        default=None,
    )

    visibility: Mapped[str | None] = mapped_column(
        VisibilityType,
        nullable=True,
        default=None,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
