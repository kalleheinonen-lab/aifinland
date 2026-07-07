"""DocumentAsset model -- always tenant-scoped (organization_id NOT NULL)."""

from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import EntityMetadataMixin


class DocumentAsset(EntityMetadataMixin, Base):
    """Document asset entity.

    Always tenant-scoped: organization_id is NOT NULL.
    Represents an uploaded document stored in object storage.
    """

    __tablename__ = "document_assets"

    # --- Override organization_id to be NOT NULL ---
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", use_alter=True, name="fk_document_assets_organization"),
        nullable=False,
    )

    # --- Business columns ---
    object_storage_key: Mapped[str] = mapped_column(String, nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    uploader_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", name="fk_document_assets_uploader_user"),
        nullable=False,
    )
    extraction_status: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    extracted_text_ref: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
