"""SQLAlchemy 2.0 declarative base with PostgreSQL type mappings."""

from __future__ import annotations

import uuid

from sqlalchemy import MetaData, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase

# Naming convention that enables %(table_name)s interpolation in FK constraint
# names.  Without this, ForeignKey(name="fk_%(table_name)s_...") is treated as
# a literal string, so every table using EntityMetadataMixin would register the
# same three constraint names and fail at DDL time with a duplicate-name error.
_NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Project-wide declarative base.

    metadata.naming_convention ensures that %(table_name)s tokens in FK
    constraint names are interpolated correctly, so EntityMetadataMixin can be
    shared across all tenant-scoped models without duplicate constraint names.

    type_annotation_map ensures that:
    - uuid.UUID columns map to PostgreSQL UUID (native)
    - dict columns map to PostgreSQL JSONB
    """

    metadata = MetaData(naming_convention=_NAMING_CONVENTION)

    type_annotation_map = {
        uuid.UUID: Uuid(as_uuid=True, native_uuid=True),
        dict: JSONB(),
    }
