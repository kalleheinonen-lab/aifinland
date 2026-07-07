"""EnrichmentRecord model -- always tenant-scoped (organization_id NOT NULL)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import EntityMetadataMixin


class EnrichmentRecord(EntityMetadataMixin, Base):
    """Enrichment record entity.

    Always tenant-scoped: organization_id is NOT NULL.
    Represents an AI-extracted or enriched data field.
    """

    __tablename__ = "enrichment_records"

    # --- Override organization_id to be NOT NULL ---
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", use_alter=True, name="fk_enrichment_records_organization"),
        nullable=False,
    )

    # --- Business columns ---
    field_path: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    extraction_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    normalized_value: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    human_validation_status: Mapped[str | None] = mapped_column(
        String, nullable=True, default="pending"
    )
