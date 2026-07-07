"""AuditLog model -- append-only, immutable (no soft delete)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import uuid7


class AuditLog(Base):
    """Audit log entity.

    Append-only: no updated_at, no deleted_at, no soft delete.
    The application role may SELECT but MUST NOT INSERT, UPDATE, or DELETE.
    Writes are performed by the BYPASSRLS migration/service role only.
    """

    __tablename__ = "audit_logs"

    # --- Primary key ---
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)

    # --- Audit columns ---
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", name="fk_audit_logs_actor_user"),
        nullable=True,
        default=None,
    )
    actor_ip: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", name="fk_audit_logs_organization"),
        nullable=True,
        default=None,
    )
    action_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    before_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
    after_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)  # type: ignore[type-arg]
    result: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    session_id: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
