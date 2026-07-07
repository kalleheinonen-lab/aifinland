"""Structural verification tests for RLS tenant isolation policies.

These tests verify the STRUCTURE of RLS policies by parsing migration SQL.
They are static/structural checks, not behavioral integration tests against
a live database. (Behavioral verification -- SET org to A, INSERT, SET org
to B, assert invisible -- requires a running PostgreSQL instance and is
deferred to a future initiative with docker-compose-based integration tests.)

# kills: missing FORCE RLS, wrong session variable name, missing OR NULL
#        clause on nullable-org tables, audit_logs having INSERT/UPDATE/DELETE
#        policies for app role, standard table accidentally using OR NULL
"""

from __future__ import annotations

import re

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SELF_KEYED_TABLES: frozenset[str] = frozenset({"organizations"})
NULLABLE_ORG_TABLES: frozenset[str] = frozenset({"users", "consortia"})
SPECIAL_RLS_TABLES: frozenset[str] = frozenset({"audit_logs"})

# Standard tables: all tenant-scoped tables that use the basic pattern
STANDARD_TABLES: frozenset[str] = frozenset({
    "memberships",
    "buyer_need_descriptions",
    "product_cards",
    "reference_cards",
    "pilot_matches",
    "ai_projects",
    "lumi_jobs",
    "document_assets",
    "enrichment_records",
})

ALL_RLS_TABLES = SELF_KEYED_TABLES | NULLABLE_ORG_TABLES | SPECIAL_RLS_TABLES | STANDARD_TABLES


# ---------------------------------------------------------------------------
# AC-1: Every tenant-scoped table has RLS policies in migration SQL
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("table_name", sorted(ALL_RLS_TABLES))
def test_ac1_table_has_enable_rls(table_name: str, all_migration_text: str) -> None:
    """AC-1: every tenant-scoped table must have ENABLE ROW LEVEL SECURITY."""
    # Check for either helper function call or direct SQL
    helper_re = re.compile(
        rf'apply_rls_policy(?:_nullable_org|_self_keyed)?\s*\(\s*op\s*,\s*["\']'
        rf'{re.escape(table_name)}["\']'
    )
    enable_re = re.compile(
        rf'ALTER\s+TABLE\s+{re.escape(table_name)}\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY',
        re.IGNORECASE,
    )
    # AC-1: expect RLS enabled for this table
    assert helper_re.search(all_migration_text) or enable_re.search(all_migration_text), (
        f"Table '{table_name}' has no RLS policy in any migration file."
    )


# ---------------------------------------------------------------------------
# AC-2: Organizations uses self-keyed pattern (id = current_setting)
# ---------------------------------------------------------------------------


def test_ac2_organizations_self_keyed_pattern(all_migration_text: str) -> None:
    """AC-2: organizations table must use id = current_setting('app.current_organization_id')::uuid."""
    # The rls.py helper for self-keyed uses:
    # id = current_setting('app.current_organization_id')::uuid
    self_keyed_re = re.compile(
        r'apply_rls_policy_self_keyed\s*\(\s*op\s*,\s*["\']organizations["\']'
    )
    # AC-2: expect self-keyed pattern for organizations
    assert self_keyed_re.search(all_migration_text), (
        "organizations must use apply_rls_policy_self_keyed (id = current_setting pattern)"
    )


def test_ac2_self_keyed_uses_id_not_organization_id() -> None:
    """AC-2: verify the self-keyed helper uses 'id' column, not 'organization_id'."""
    import inspect

    from app.db.rls import apply_rls_policy_self_keyed

    source = inspect.getsource(apply_rls_policy_self_keyed)
    # AC-2: expect 'id = current_setting' in the source
    assert "id = current_setting('app.current_organization_id')::uuid" in source


# ---------------------------------------------------------------------------
# AC-3: Users and consortia use OR organization_id IS NULL clause
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("table_name", sorted(NULLABLE_ORG_TABLES))
def test_ac3_nullable_org_tables_use_or_null(
    table_name: str, all_migration_text: str
) -> None:
    """AC-3: users and consortia must use OR organization_id IS NULL clause."""
    nullable_re = re.compile(
        rf'apply_rls_policy_nullable_org\s*\(\s*op\s*,\s*["\']'
        rf'{re.escape(table_name)}["\']'
    )
    # AC-3: expect nullable-org pattern for this table
    assert nullable_re.search(all_migration_text), (
        f"Table '{table_name}' must use apply_rls_policy_nullable_org "
        "(includes OR organization_id IS NULL clause)"
    )


def test_ac3_nullable_org_helper_includes_or_null() -> None:
    """AC-3: verify the nullable-org helper includes OR organization_id IS NULL."""
    import inspect

    from app.db.rls import apply_rls_policy_nullable_org

    source = inspect.getsource(apply_rls_policy_nullable_org)
    # AC-3: expect OR NULL clause in the helper
    assert "OR organization_id IS NULL" in source


# ---------------------------------------------------------------------------
# AC-4: Standard tables use organization_id without OR NULL
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("table_name", sorted(STANDARD_TABLES))
def test_ac4_standard_tables_use_standard_policy(
    table_name: str, all_migration_text: str
) -> None:
    """AC-4: standard tables must use apply_rls_policy (not nullable or self-keyed)."""
    # Must match apply_rls_policy(op, "table_name") but NOT apply_rls_policy_nullable_org
    # or apply_rls_policy_self_keyed
    standard_re = re.compile(
        rf'apply_rls_policy\s*\(\s*op\s*,\s*["\']'
        rf'{re.escape(table_name)}["\']'
    )
    # AC-4: expect standard pattern for this table
    assert standard_re.search(all_migration_text), (
        f"Table '{table_name}' must use apply_rls_policy (standard pattern without OR NULL)"
    )


def test_ac4_standard_helper_does_not_include_or_null() -> None:
    """AC-4: verify the standard helper does NOT include OR organization_id IS NULL."""
    import inspect

    from app.db.rls import apply_rls_policy

    source = inspect.getsource(apply_rls_policy)
    # AC-4: expect no OR NULL clause in the standard helper
    assert "OR organization_id IS NULL" not in source


# ---------------------------------------------------------------------------
# AC-5: RLS policies reference 'app.current_organization_id' session variable
# ---------------------------------------------------------------------------


def test_ac5_session_variable_referenced() -> None:
    """AC-5: all RLS helpers must reference 'app.current_organization_id' session variable."""
    import inspect

    from app.db import rls

    source = inspect.getsource(rls)
    # AC-5: expect session variable name in the module
    assert "app.current_organization_id" in source


# ---------------------------------------------------------------------------
# AC-6: FORCE ROW LEVEL SECURITY is set (table owners subject to RLS)
# ---------------------------------------------------------------------------


def test_ac6_force_rls_in_helper() -> None:
    """AC-6: the _enable_rls helper must issue FORCE ROW LEVEL SECURITY."""
    import inspect

    from app.db import rls

    source = inspect.getsource(rls)
    # AC-6: expect FORCE ROW LEVEL SECURITY in the module
    assert "FORCE ROW LEVEL SECURITY" in source


def test_ac6_force_rls_for_audit_logs(all_migration_text: str) -> None:
    """AC-6: audit_logs must also have FORCE ROW LEVEL SECURITY."""
    force_re = re.compile(
        r'ALTER\s+TABLE\s+audit_logs\s+FORCE\s+ROW\s+LEVEL\s+SECURITY',
        re.IGNORECASE,
    )
    # AC-6: expect FORCE RLS for audit_logs
    assert force_re.search(all_migration_text), (
        "audit_logs must have FORCE ROW LEVEL SECURITY set"
    )


# ---------------------------------------------------------------------------
# AC-7: audit_logs has SELECT-only policy (no INSERT/UPDATE/DELETE for app role)
# ---------------------------------------------------------------------------


def test_ac7_audit_logs_has_select_policy(all_migration_text: str) -> None:
    """AC-7: audit_logs must have a SELECT policy."""
    select_re = re.compile(
        r'CREATE\s+POLICY\s+\w+\s+ON\s+audit_logs\s+'
        r'FOR\s+SELECT',
        re.IGNORECASE,
    )
    # AC-7: expect SELECT policy on audit_logs
    assert select_re.search(all_migration_text), (
        "audit_logs must have a SELECT policy for the app role"
    )


def test_ac7_audit_logs_no_insert_policy(all_migration_text: str) -> None:
    """AC-7: audit_logs must NOT have an INSERT policy for the app role."""
    insert_re = re.compile(
        r'CREATE\s+POLICY\s+\w+\s+ON\s+audit_logs\s+'
        r'FOR\s+INSERT',
        re.IGNORECASE,
    )
    # AC-7: expect NO INSERT policy on audit_logs
    assert not insert_re.search(all_migration_text), (
        "audit_logs must NOT have an INSERT policy (append-only via BYPASSRLS role)"
    )


def test_ac7_audit_logs_no_update_policy(all_migration_text: str) -> None:
    """AC-7: audit_logs must NOT have an UPDATE policy for the app role."""
    update_re = re.compile(
        r'CREATE\s+POLICY\s+\w+\s+ON\s+audit_logs\s+'
        r'FOR\s+UPDATE',
        re.IGNORECASE,
    )
    # AC-7: expect NO UPDATE policy on audit_logs
    assert not update_re.search(all_migration_text), (
        "audit_logs must NOT have an UPDATE policy (immutable)"
    )


def test_ac7_audit_logs_no_delete_policy(all_migration_text: str) -> None:
    """AC-7: audit_logs must NOT have a DELETE policy for the app role."""
    delete_re = re.compile(
        r'CREATE\s+POLICY\s+\w+\s+ON\s+audit_logs\s+'
        r'FOR\s+DELETE',
        re.IGNORECASE,
    )
    # AC-7: expect NO DELETE policy on audit_logs
    assert not delete_re.search(all_migration_text), (
        "audit_logs must NOT have a DELETE policy (immutable)"
    )
