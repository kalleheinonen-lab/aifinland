"""User model -- inherits EntityMetadataMixin with nullable organization_id."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import EntityMetadataMixin
from app.db.types import UserStatusType


class User(EntityMetadataMixin, Base):
    """User entity.

    Platform-scoped users (SuperAdmin, Admin) have organization_id=NULL.
    RLS policy for users includes an OR clause:
        organization_id = current_setting('app.current_organization_id')::uuid
        OR organization_id IS NULL
    so platform-scoped users remain visible to all tenants.
    Write access for NULL-org users is restricted to BYPASSRLS migration role.
    """

    __tablename__ = "users"

    # --- Business columns ---
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    username: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        UserStatusType,
        nullable=False,
        default="Active",
    )
    preferred_language: Mapped[str] = mapped_column(String, nullable=False, default="fi")
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mfa_secret: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    force_password_reset: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
