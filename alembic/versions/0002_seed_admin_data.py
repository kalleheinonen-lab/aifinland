"""Seed data: AI Finland organization and Super Admin user account.

Revision ID: 0002
Revises: 0001
Create Date: 2025-01-01 00:00:01.000000

Security notes:
- The bcrypt password hash below is pre-computed at cost factor 12.
- The plaintext credential appears ONLY in the project spec (SEC-1);
  it does NOT appear anywhere in source code.
- force_password_reset=True ensures the Super Admin must change the
  password on first login.
- The Super Admin user has organization_id=NULL (platform-scoped);
  their association to AI Finland is via the Membership record.

RLS bypass:
- This migration runs as the table owner role which has BYPASSRLS
  privilege. No SET app.current_organization_id is required for
  seed inserts.

Idempotency:
- All inserts use ON CONFLICT (id) DO NOTHING so re-running the
  migration is safe.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.db.seed import AI_FINLAND_ORG_ID, SUPER_ADMIN_MEMBERSHIP_ID, SUPER_ADMIN_USER_ID

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# ---------------------------------------------------------------------------
# Seed constants
# ---------------------------------------------------------------------------

# Pre-computed bcrypt hash (cost factor 12) of the bootstrap credential.
# The plaintext MUST NOT appear in source code -- see spec SEC-1.
_SUPER_ADMIN_PASSWORD_HASH = (
    "$2b$12$YtA.piUev9ojCKZVOrgwsO0pOG2qmSVgztOw/x1OyZ1It580fXLnu"
)


def upgrade() -> None:
    """Insert AI Finland org, Super Admin user, and their membership record."""

    # ------------------------------------------------------------------
    # 1. AI Finland organization (platform operator)
    # ------------------------------------------------------------------
    # organization_type='Other' is the closest available enum value;
    # there is no 'PlatformOperator' member in the organizationtype enum.
    # visibility is NULL: 'platform_wide' is not a valid visibility enum
    # value; the platform-wide nature is expressed via the SuperAdmin role.
    op.execute(
        sa.text("""
            INSERT INTO organizations (
                id,
                name,
                organization_type,
                status,
                visibility,
                created_at,
                updated_at
            ) VALUES (
                :id,
                'AI Finland',
                'Other',
                'active',
                NULL,
                now(),
                now()
            )
            ON CONFLICT (id) DO NOTHING
        """).bindparams(id=str(AI_FINLAND_ORG_ID))
    )

    # ------------------------------------------------------------------
    # 2. Super Admin user (platform-scoped, organization_id=NULL)
    # ------------------------------------------------------------------
    op.execute(
        sa.text("""
            INSERT INTO users (
                id,
                email,
                display_name,
                password_hash,
                status,
                force_password_reset,
                mfa_enabled,
                organization_id,
                created_at,
                updated_at
            ) VALUES (
                :id,
                'kalle@aifinland.fi',
                'Kalle Admin',
                :password_hash,
                'Active',
                TRUE,
                FALSE,
                NULL,
                now(),
                now()
            )
            ON CONFLICT (id) DO NOTHING
        """).bindparams(
            id=str(SUPER_ADMIN_USER_ID),
            password_hash=_SUPER_ADMIN_PASSWORD_HASH,
        )
    )

    # ------------------------------------------------------------------
    # 3. Membership: Super Admin <-> AI Finland org
    # ------------------------------------------------------------------
    op.execute(
        sa.text("""
            INSERT INTO memberships (
                id,
                user_id,
                organization_id,
                role,
                status,
                created_at,
                updated_at
            ) VALUES (
                :id,
                :user_id,
                :org_id,
                'SuperAdmin',
                'Active',
                now(),
                now()
            )
            ON CONFLICT (id) DO NOTHING
        """).bindparams(
            id=str(SUPER_ADMIN_MEMBERSHIP_ID),
            user_id=str(SUPER_ADMIN_USER_ID),
            org_id=str(AI_FINLAND_ORG_ID),
        )
    )


def downgrade() -> None:
    """Remove the seed records by their fixed UUIDs (reverse insertion order)."""

    # Delete membership first (FK dependency on users and organizations)
    op.execute(
        sa.text("DELETE FROM memberships WHERE id = :membership_id").bindparams(
            membership_id=str(SUPER_ADMIN_MEMBERSHIP_ID)
        )
    )

    # Delete Super Admin user
    op.execute(
        sa.text("DELETE FROM users WHERE id = :user_id").bindparams(
            user_id=str(SUPER_ADMIN_USER_ID)
        )
    )

    # Delete AI Finland organization
    op.execute(
        sa.text("DELETE FROM organizations WHERE id = :org_id").bindparams(
            org_id=str(AI_FINLAND_ORG_ID)
        )
    )
