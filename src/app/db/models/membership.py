"""Membership model -- always tenant-scoped (organization_id NOT NULL)."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import EntityMetadataMixin
from app.db.types import MembershipRoleType, MembershipStatusType


class Membership(EntityMetadataMixin, Base):
    """Membership entity -- links a user to an organization with a role.

    Always tenant-scoped: organization_id is NOT NULL.
    UniqueConstraint on (user_id, organization_id) prevents duplicate memberships.
    """

    __tablename__ = "memberships"

    # --- Override organization_id to be NOT NULL ---
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", use_alter=True, name="fk_memberships_organization"),
        nullable=False,
    )

    # --- Business columns ---
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        MembershipRoleType,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        MembershipStatusType,
        nullable=False,
        default="Active",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_memberships_user_organization"),
    )
