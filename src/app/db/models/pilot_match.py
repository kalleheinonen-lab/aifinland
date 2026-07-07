"""PilotMatch model -- tenant-scoped via demand_organization_id."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import EntityMetadataMixin
from app.db.types import PilotMatchStatusType


class PilotMatch(EntityMetadataMixin, Base):
    """Pilot match entity.

    Tenant-scoped: organization_id is set to demand_organization_id.
    Represents a match between a buyer need and a product.
    """

    __tablename__ = "pilot_matches"

    # --- Override organization_id to be NOT NULL (set to demand_organization_id) ---
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", use_alter=True, name="fk_pilot_matches_organization"),
        nullable=False,
    )

    # --- Business columns ---
    need_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("buyer_need_descriptions.id"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_cards.id"),
        nullable=False,
    )
    demand_organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", name="fk_pilot_matches_demand_organization"),
        nullable=False,
    )
    supply_organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", name="fk_pilot_matches_supply_organization"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        PilotMatchStatusType,
        nullable=False,
        default="Candidate",
    )
    signals: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
    lumi_score: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    demand_approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    contact_shared_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    supply_notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
