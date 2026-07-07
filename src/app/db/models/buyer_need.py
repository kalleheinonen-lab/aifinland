"""BuyerNeedDescription model -- always tenant-scoped (organization_id NOT NULL)."""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import EntityMetadataMixin
from app.db.types import NeedStatusType


class BuyerNeedDescription(EntityMetadataMixin, Base):
    """Buyer need description entity.

    Always tenant-scoped: organization_id is NOT NULL.
    Represents a structured buyer need used for AI matchmaking.
    """

    __tablename__ = "buyer_need_descriptions"

    # --- Override organization_id to be NOT NULL ---
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", use_alter=True, name="fk_buyer_need_descriptions_organization"),
        nullable=False,
    )

    # --- Business columns ---
    version: Mapped[str] = mapped_column(String, nullable=False, default="v1.0")
    status: Mapped[str] = mapped_column(
        NeedStatusType,
        nullable=False,
        default="Draft",
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    problem_summary: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    target_outcome: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    specific_requirements: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
    success_criteria: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
    technical_constraints: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
    timeline: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
    budget_range: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
    vendor_priorities: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
    readiness_score: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    source_conversation_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, default=None)
