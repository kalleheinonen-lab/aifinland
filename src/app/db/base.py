"""SQLAlchemy 2.0 declarative base with PostgreSQL type mappings."""

from __future__ import annotations

import uuid

from sqlalchemy import Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Project-wide declarative base.

    type_annotation_map ensures that:
    - uuid.UUID columns map to PostgreSQL UUID (native)
    - dict columns map to PostgreSQL JSONB
    """

    type_annotation_map = {
        uuid.UUID: Uuid(as_uuid=True, native_uuid=True),
        dict: JSONB(),
    }
