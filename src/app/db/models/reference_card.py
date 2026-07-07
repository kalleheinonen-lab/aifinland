"""ReferenceCard model -- always tenant-scoped (organization_id NOT NULL)."""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import EntityMetadataMixin


class ReferenceCard(EntityMetadataMixin, Base):
    """Reference card entity.

    Always tenant-scoped: organization_id is NOT NULL.
    Represents a customer reference/case study for a product.
    """

    __tablename__ = "reference_cards"

    # --- Override organization_id to be NOT NULL ---
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", use_alter=True, name="fk_reference_cards_organization"),
        nullable=False,
    )

    # --- Business columns ---
    version: Mapped[str] = mapped_column(String, nullable=False, default="v1.0")
    reference_type: Mapped[str] = mapped_column(String, nullable=False, default="anonymous")
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    customer_industry: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    customer_size: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    measurable_result: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    timeline: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
    technologies_used: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
    provider_role: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    starting_situation_and_problem: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    solution_approach: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    ai_extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product_cards.id"),
        nullable=True,
        default=None,
    )
