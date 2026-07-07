"""Consortium model -- platform-scoped (organization_id nullable)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import EntityMetadataMixin
from app.db.types import ConsortiumStatusType


class Consortium(EntityMetadataMixin, Base):
    """Consortium entity.

    Platform-scoped: organization_id is nullable (inherited from mixin).
    Represents a consortium formed around a buyer need.
    """

    __tablename__ = "consortia"

    # --- Business columns ---
    problem_statement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("buyer_need_descriptions.id"),
        nullable=True,
        default=None,
    )
    status: Mapped[str] = mapped_column(
        ConsortiumStatusType,
        nullable=False,
        default="ProblemStatementComplete",
    )
    participants: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
    candidate_organizations: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
    question_set_version: Mapped[str] = mapped_column(String, nullable=False, default="v1.0")
    match_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
    finalized_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", name="fk_consortia_finalized_by_user"),
        nullable=True,
        default=None,
    )
    finalized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
