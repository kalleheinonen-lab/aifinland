"""CI gate tests: every tenant-scoped table must have RLS in a migration.

# kills: missing RLS on a new organization_id table, wrong RLS pattern on
#        organizations (organization_id instead of id), uncovered table added
#        without migration update
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers (mirrors scripts/check_rls_coverage.py logic)
# ---------------------------------------------------------------------------

SELF_KEYED_TABLES: frozenset[str] = frozenset({"organizations"})
NULLABLE_ORG_TABLES: frozenset[str] = frozenset({"users", "consortia"})
SPECIAL_RLS_TABLES: frozenset[str] = frozenset({"audit_logs"})

_VERSIONS_DIR = Path(__file__).resolve().parent.parent / "alembic" / "versions"


def _tables_needing_rls() -> frozenset[str]:
    """Return all table names that must have RLS, derived from SQLAlchemy metadata."""
    import app.db.models  # noqa: F401  (side-effect: populates Base.metadata)
    from app.db.base import Base

    standard: set[str] = set()
    for table_name, table in Base.metadata.tables.items():
        col_names = {col.name for col in table.columns}
        if "organization_id" in col_names:
            if table_name not in NULLABLE_ORG_TABLES and table_name not in SPECIAL_RLS_TABLES:
                standard.add(table_name)

    return SELF_KEYED_TABLES | NULLABLE_ORG_TABLES | SPECIAL_RLS_TABLES | frozenset(standard)


def _covered_tables_from_migrations() -> set[str]:
    """Parse migration files and return the set of RLS-covered table names."""
    covered: set[str] = set()
    helper_re = re.compile(
        r'apply_rls_policy(?:_nullable_org|_self_keyed)?\s*\(\s*op\s*,\s*["\']([\w]+)["\']'
    )
    enable_re = re.compile(
        r'ALTER\s+TABLE\s+(\w+)\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY',
        re.IGNORECASE,
    )
    for migration_file in sorted(_VERSIONS_DIR.glob("*.py")):
        text = migration_file.read_text(encoding="utf-8")
        for match in helper_re.finditer(text):
            covered.add(match.group(1))
        for match in enable_re.finditer(text):
            covered.add(match.group(1))
    return covered


def _all_migration_text() -> str:
    """Return concatenated text of all migration files."""
    parts = []
    for migration_file in sorted(_VERSIONS_DIR.glob("*.py")):
        parts.append(migration_file.read_text(encoding="utf-8"))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_ac_rls_versions_dir_exists() -> None:
    """AC-rls-1: alembic/versions/ directory must exist for the gate to work."""
    # AC-rls-1: expect the directory to be present
    assert _VERSIONS_DIR.is_dir(), f"alembic/versions/ not found at {_VERSIONS_DIR}"


def test_ac_rls_all_tenant_tables_covered() -> None:
    """AC-rls-2: every table with organization_id (or organizations itself) must have RLS.

    This is the primary CI gate: catches a developer adding a new model with
    organization_id but forgetting to add RLS in the migration.
    """
    needed = _tables_needing_rls()
    covered = _covered_tables_from_migrations()
    uncovered = needed - covered

    # AC-rls-2: expect no uncovered tables
    assert not uncovered, (
        "Tables need RLS but have no ENABLE ROW LEVEL SECURITY in any migration:\n"
        + "\n".join(f"  - {t}" for t in sorted(uncovered))
    )


def test_ac_rls_organizations_uses_self_keyed_pattern() -> None:
    """AC-rls-3: organizations table must use id = current_setting (self-keyed).

    Verifies that apply_rls_policy_self_keyed is used for organizations,
    not the standard organization_id-based policy.
    """
    migration_text = _all_migration_text()
    self_keyed_re = re.compile(
        r'apply_rls_policy_self_keyed\s*\(\s*op\s*,\s*["\']organizations["\']'
    )
    # AC-rls-3: expect self-keyed pattern for organizations
    assert self_keyed_re.search(migration_text), (
        "'organizations' must use apply_rls_policy_self_keyed() "
        "(id = current_setting pattern), not the standard organization_id pattern."
    )


def test_ac_rls_standard_tables_use_standard_policy() -> None:
    """AC-rls-4: standard tenant tables must use apply_rls_policy (not self-keyed).

    Verifies that tables other than organizations do NOT accidentally use
    the self-keyed pattern.
    """
    migration_text = _all_migration_text()
    # Find all tables using self-keyed pattern
    self_keyed_re = re.compile(
        r'apply_rls_policy_self_keyed\s*\(\s*op\s*,\s*["\']([\w]+)["\']'
    )
    self_keyed_tables = {m.group(1) for m in self_keyed_re.finditer(migration_text)}

    # AC-rls-4: only organizations should use self-keyed
    unexpected_self_keyed = self_keyed_tables - SELF_KEYED_TABLES
    assert not unexpected_self_keyed, (
        f"These tables unexpectedly use apply_rls_policy_self_keyed: {unexpected_self_keyed}. "
        "Only 'organizations' should use the self-keyed (id-based) pattern."
    )


def test_ac_rls_metadata_tables_match_expected_set() -> None:
    """AC-rls-5: SQLAlchemy metadata must contain all 13 expected tables.

    Ensures the model registry is complete and no table was accidentally
    removed from the metadata.
    """
    import app.db.models  # noqa: F401
    from app.db.base import Base

    actual_tables = set(Base.metadata.tables.keys())
    expected_tables = {
        "organizations",
        "users",
        "memberships",
        "buyer_need_descriptions",
        "product_cards",
        "reference_cards",
        "pilot_matches",
        "consortia",
        "ai_projects",
        "lumi_jobs",
        "audit_logs",
        "document_assets",
        "enrichment_records",
    }
    # AC-rls-5: expect all 13 tables registered in metadata
    assert expected_tables.issubset(actual_tables), (
        f"Missing tables from metadata: {expected_tables - actual_tables}"
    )


@pytest.mark.parametrize(
    "table_name",
    [
        # AC-rls-6: each known RLS table must appear in migration coverage
        pytest.param("organizations", id="organizations"),
        pytest.param("users", id="users"),
        pytest.param("consortia", id="consortia"),
        pytest.param("audit_logs", id="audit_logs"),
        pytest.param("memberships", id="memberships"),
        pytest.param("buyer_need_descriptions", id="buyer_need_descriptions"),
        pytest.param("product_cards", id="product_cards"),
        pytest.param("reference_cards", id="reference_cards"),
        pytest.param("pilot_matches", id="pilot_matches"),
        pytest.param("ai_projects", id="ai_projects"),
        pytest.param("lumi_jobs", id="lumi_jobs"),
        pytest.param("document_assets", id="document_assets"),
        pytest.param("enrichment_records", id="enrichment_records"),
    ],
)
def test_ac_rls_each_table_individually_covered(table_name: str) -> None:
    """AC-rls-6: each known tenant-scoped table is individually covered by a migration."""
    covered = _covered_tables_from_migrations()
    # AC-rls-6: expect each table to appear in migration RLS coverage
    assert table_name in covered, (
        f"Table '{table_name}' has no ENABLE ROW LEVEL SECURITY in any migration. "
        "Add RLS via apply_rls_policy*() or a direct ALTER TABLE statement."
    )
