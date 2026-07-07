"""AIProject model -- always tenant-scoped (organization_id NOT NULL)."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import EntityMetadataMixin


class AIProject(EntityMetadataMixin, Base):
    """AI project entity.

    Always tenant-scoped: organization_id is NOT NULL.
    Represents an AI project owned by an organization.
    """

    __tablename__ = "ai_projects"

    # --- Override organization_id to be NOT NULL ---
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", use_alter=True, name="fk_ai_projects_organization"),
        nullable=False,
    )

    # --- Business columns ---
    name: Mapped[str] = mapped_column(String, nullable=False)
    sector: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    region: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    maturity_stage: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    technologies: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
    funding_sources: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
    public_description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    impact_metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
