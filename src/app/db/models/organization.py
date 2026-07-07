"""Organization model -- self-keyed for RLS (no EntityMetadataMixin)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import OrganizationTypeType, VisibilityType, uuid7


class Organization(Base):
    """Organization entity.

    Does NOT inherit EntityMetadataMixin because the mixin's organization_id
    FK would create a self-referential chicken-and-egg problem for RLS.
    Instead, the org's own `id` is the RLS tenant key:
        id = current_setting('app.current_organization_id')::uuid
    """

    __tablename__ = "organizations"

    # --- Primary key ---
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)

    # --- Audit timestamps ---
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
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # --- Audit actor FKs ---
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", use_alter=True, name="fk_organizations_created_by_user"),
        nullable=True,
        default=None,
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", use_alter=True, name="fk_organizations_updated_by_user"),
        nullable=True,
        default=None,
    )

    # --- Visibility ---
    visibility: Mapped[str | None] = mapped_column(
        VisibilityType,
        nullable=True,
        default=None,
    )

    # --- Business columns ---
    name: Mapped[str] = mapped_column(String, nullable=False)
    business_id: Mapped[str | None] = mapped_column(String, nullable=True, unique=True, default=None)
    organization_type: Mapped[str | None] = mapped_column(
        OrganizationTypeType,
        nullable=True,
        default=None,
    )
    location: Mapped[dict | None] = mapped_column(nullable=True, default=None)  # type: ignore[type-arg]
    ai_maturity_level: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=None,
    )
    capabilities: Mapped[dict | None] = mapped_column(nullable=True, default=None)  # type: ignore[type-arg]
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")

    __table_args__ = (
        CheckConstraint(
            "ai_maturity_level IS NULL OR (ai_maturity_level >= 1 AND ai_maturity_level <= 5)",
            name="ai_maturity_level_range",
        ),
    )
