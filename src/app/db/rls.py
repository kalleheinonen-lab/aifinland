"""Row-Level Security (RLS) helper functions for Alembic migrations.

These functions are called from migration scripts to apply or remove
RLS policies on tenant-scoped tables. Three patterns exist:

1. Standard: organization_id = current_setting('app.current_organization_id')::uuid
2. Self-keyed: id = current_setting('app.current_organization_id')::uuid (organizations table)
3. Nullable-org: organization_id = ... OR organization_id IS NULL (users, consortia)
"""

from __future__ import annotations

from typing import Any

_OPERATIONS = ("select", "insert", "update", "delete")


def apply_rls_policy(alembic_op: Any, table_name: str) -> None:
    """Apply standard RLS policies using organization_id as the isolation key.

    Args:
        alembic_op: The Alembic op module (passed for explicitness).
        table_name: The database table name to protect.
    """
    _enable_rls(alembic_op, table_name)
    condition = (
        "organization_id = current_setting('app.current_organization_id')::uuid"
    )
    _create_policies(alembic_op, table_name, condition)


def apply_rls_policy_self_keyed(alembic_op: Any, table_name: str) -> None:
    """Apply RLS policies for the organizations table (self-keyed).

    Uses `id` instead of `organization_id` as the isolation column.

    Args:
        alembic_op: The Alembic op module (passed for explicitness).
        table_name: The database table name to protect.
    """
    _enable_rls(alembic_op, table_name)
    condition = "id = current_setting('app.current_organization_id')::uuid"
    _create_policies(alembic_op, table_name, condition)


def apply_rls_policy_nullable_org(alembic_op: Any, table_name: str) -> None:
    """Apply RLS policies for tables where organization_id is nullable.

    Rows with NULL organization_id (platform-scoped) remain visible.

    Args:
        alembic_op: The Alembic op module (passed for explicitness).
        table_name: The database table name to protect.
    """
    _enable_rls(alembic_op, table_name)
    condition = (
        "organization_id = current_setting('app.current_organization_id')::uuid "
        "OR organization_id IS NULL"
    )
    _create_policies(alembic_op, table_name, condition)


def drop_rls_policy(alembic_op: Any, table_name: str) -> None:
    """Remove all RLS policies and disable RLS on a table (for downgrade).

    Args:
        alembic_op: The Alembic op module (passed for explicitness).
        table_name: The database table name.
    """
    for operation in _OPERATIONS:
        policy_name = f"{table_name}_{operation}_policy"
        alembic_op.execute(
            f"DROP POLICY IF EXISTS {policy_name} ON {table_name}"
        )
    alembic_op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _enable_rls(alembic_op: Any, table_name: str) -> None:
    """Enable and force RLS on a table."""
    alembic_op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
    alembic_op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")


def _create_policies(
    alembic_op: Any, table_name: str, condition: str
) -> None:
    """Create SELECT/INSERT/UPDATE/DELETE policies with the given condition."""
    for operation in _OPERATIONS:
        policy_name = f"{table_name}_{operation}_policy"
        if operation == "insert":
            clause = f"WITH CHECK ({condition})"
        elif operation == "update":
            clause = f"USING ({condition}) WITH CHECK ({condition})"
        else:
            clause = f"USING ({condition})"
        alembic_op.execute(
            f"CREATE POLICY {policy_name} ON {table_name} "
            f"FOR {operation.upper()} "
            f"{clause}"
        )
