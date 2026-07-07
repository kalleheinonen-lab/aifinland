"""Seed data constants for the AI Finland platform.

These UUIDs are fixed (hardcoded) for reproducibility across environments.
Import them in tests and application code to reference the canonical
platform-operator organization and the bootstrap Super Admin user.
"""

from __future__ import annotations

import uuid

# Fixed UUIDv7 for the AI Finland platform-operator organization.
# Created by migration 0002_seed_admin_data.
AI_FINLAND_ORG_ID: uuid.UUID = uuid.UUID("01912345-6789-7abc-8def-0123456789ab")

# Fixed UUIDv7 for the bootstrap Super Admin user (kalle@aifinland.fi).
# Created by migration 0002_seed_admin_data.
SUPER_ADMIN_USER_ID: uuid.UUID = uuid.UUID("01912345-6789-7abc-8def-0123456789cd")

# Fixed UUIDv7 for the Super Admin membership record.
# Created by migration 0002_seed_admin_data.
SUPER_ADMIN_MEMBERSHIP_ID: uuid.UUID = uuid.UUID("01912345-6789-7abc-8def-0123456789ef")
