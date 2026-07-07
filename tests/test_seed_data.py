"""Seed data contract tests: verify the seed migration and constants.

# kills: invalid UUID constants, wrong email in seed, missing force_password_reset,
#        non-bcrypt hash, missing ON CONFLICT (not idempotent), SuperAdmin with
#        non-NULL organization_id
"""

from __future__ import annotations

import uuid

from app.db.seed import AI_FINLAND_ORG_ID, SUPER_ADMIN_USER_ID

# ---------------------------------------------------------------------------
# AC-1: AI_FINLAND_ORG_ID and SUPER_ADMIN_USER_ID are valid UUIDs
# ---------------------------------------------------------------------------


def test_ac1_ai_finland_org_id_is_valid_uuid() -> None:
    """AC-1: AI_FINLAND_ORG_ID must be a valid UUID."""
    # AC-1: expect valid UUID instance
    assert isinstance(AI_FINLAND_ORG_ID, uuid.UUID)
    # Verify it can round-trip through string representation
    assert uuid.UUID(str(AI_FINLAND_ORG_ID)) == AI_FINLAND_ORG_ID


def test_ac1_super_admin_user_id_is_valid_uuid() -> None:
    """AC-1: SUPER_ADMIN_USER_ID must be a valid UUID."""
    # AC-1: expect valid UUID instance
    assert isinstance(SUPER_ADMIN_USER_ID, uuid.UUID)
    assert uuid.UUID(str(SUPER_ADMIN_USER_ID)) == SUPER_ADMIN_USER_ID


# ---------------------------------------------------------------------------
# AC-2: Seed migration contains INSERT for correct email
# ---------------------------------------------------------------------------


def test_ac2_seed_contains_correct_email(seed_migration_text: str) -> None:
    """AC-2: seed migration must INSERT the correct email 'kalle@aifinland.fi'."""
    # AC-2: expect the email in the migration
    assert "kalle@aifinland.fi" in seed_migration_text


# ---------------------------------------------------------------------------
# AC-3: Seed migration sets force_password_reset = True
# ---------------------------------------------------------------------------


def test_ac3_force_password_reset_true(seed_migration_text: str) -> None:
    """AC-3: seed migration must set force_password_reset = TRUE."""
    # AC-3: expect TRUE for force_password_reset
    assert "force_password_reset" in seed_migration_text
    # The SQL uses TRUE (PostgreSQL boolean literal)
    assert "TRUE" in seed_migration_text


# ---------------------------------------------------------------------------
# AC-4: Seed migration uses bcrypt hash (starts with '$2b$12$')
# ---------------------------------------------------------------------------


def test_ac4_bcrypt_hash_present(seed_migration_text: str) -> None:
    """AC-4: seed migration must use bcrypt hash (starts with '$2b$12$')."""
    # AC-4: expect bcrypt cost-12 hash prefix
    assert "$2b$12$" in seed_migration_text


# ---------------------------------------------------------------------------
# AC-5: Seed migration is idempotent (ON CONFLICT DO NOTHING)
# ---------------------------------------------------------------------------


def test_ac5_idempotent_on_conflict(seed_migration_text: str) -> None:
    """AC-5: seed migration must use ON CONFLICT DO NOTHING for idempotency."""
    # AC-5: expect ON CONFLICT DO NOTHING
    assert "ON CONFLICT" in seed_migration_text
    assert "DO NOTHING" in seed_migration_text
    # Count occurrences: should be at least 3 (org, user, membership)
    assert seed_migration_text.count("ON CONFLICT") >= 3


# ---------------------------------------------------------------------------
# AC-6: SuperAdmin user has organization_id as NULL (platform-scoped)
# ---------------------------------------------------------------------------


def test_ac6_super_admin_organization_id_null(seed_migration_text: str) -> None:
    """AC-6: SuperAdmin user must have organization_id = NULL (platform-scoped)."""
    # The INSERT for users includes organization_id with value NULL
    # AC-6: expect NULL for organization_id in the users INSERT
    # Find the users INSERT block and verify it contains NULL for organization_id
    assert "organization_id" in seed_migration_text
    # The SQL sets organization_id to NULL explicitly
    # Look for the pattern in the users INSERT (between user INSERT markers)
    lines = seed_migration_text.split("\n")
    in_user_insert = False
    found_null_org = False
    for line in lines:
        if "INSERT INTO users" in line:
            in_user_insert = True
        if in_user_insert and "ON CONFLICT" in line:
            in_user_insert = False
        if in_user_insert and "NULL" in line:
            found_null_org = True
            break
    # AC-6: expect NULL in the users INSERT block
    assert found_null_org, (
        "SuperAdmin user INSERT must set organization_id to NULL (platform-scoped)"
    )
