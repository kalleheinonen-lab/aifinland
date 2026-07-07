"""LumiJob model -- tenant-scoped (organization_id maps to tenant_id)."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import EntityMetadataMixin


class LumiJob(EntityMetadataMixin, Base):
    """Lumi AI job entity.

    Tenant-scoped: organization_id maps to the tenant_id concept.
    Represents an asynchronous AI processing job.
    """

    __tablename__ = "lumi_jobs"

    # --- Business columns ---
    request_id: Mapped[uuid.UUID] = mapped_column(unique=True, nullable=False)
    use_case: Mapped[str] = mapped_column(String, nullable=False)
    caller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", name="fk_lumi_jobs_caller_user"),
        nullable=False,
    )
    input: Mapped[dict] = mapped_column(JSONB, nullable=False)  # type: ignore[type-arg]
    filters: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    model_version: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    results: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
    diagnostics: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
