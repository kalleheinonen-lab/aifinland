"""ProductCard model -- always tenant-scoped (organization_id NOT NULL)."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import EntityMetadataMixin
from app.db.types import ProductStatusType


class ProductCard(EntityMetadataMixin, Base):
    """Product card entity.

    Always tenant-scoped: organization_id is NOT NULL.
    Represents a vendor's AI product offering.
    """

    __tablename__ = "product_cards"

    # --- Override organization_id to be NOT NULL ---
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", use_alter=True, name="fk_product_cards_organization"),
        nullable=False,
    )

    # --- Business columns ---
    version: Mapped[str] = mapped_column(String, nullable=False, default="v1.0")
    status: Mapped[str] = mapped_column(
        ProductStatusType,
        nullable=False,
        default="Draft",
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    product_version: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    short_description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    demo: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
    pricing_model: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    price_range: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
    hosting_location: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    certifications: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
    readiness: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
    implementation_time: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    pilot_settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
