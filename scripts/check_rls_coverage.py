#!/usr/bin/env python3
"""CI gate: verify every tenant-scoped table has RLS enabled in a migration.

Exits 0 when all tables are covered, exits 1 with a clear error listing
any uncovered tables.

Usage:
    python scripts/check_rls_coverage.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# RLS table categories
# ---------------------------------------------------------------------------

# Pattern 1: id = current_setting('app.current_organization_id')::uuid
SELF_KEYED_TABLES: frozenset[str] = frozenset({"organizations"})

# Pattern 2: organization_id = ... OR organization_id IS NULL
NULLABLE_ORG_TABLES: frozenset[str] = frozenset({"users", "consortia"})

# Special: SELECT-only policy (append-only audit table)
SPECIAL_RLS_TABLES: frozenset[str] = frozenset({"audit_logs"})

# Pattern 3: standard -- populated dynamically from SQLAlchemy metadata
# (all tables with an 'organization_id' column not already in the above sets)


def _collect_all_rls_tables() -> frozenset[str]:
    """Import models and return the set of all tables that need RLS."""
    # Import models so that Base.metadata is populated.
    import app.db.models  # noqa: F401  (side-effect: registers all models)
    from app.db.base import Base

    standard: set[str] = set()
    for table_name, table in Base.metadata.tables.items():
        col_names = {col.name for col in table.columns}
        if "organization_id" in col_names:
            if table_name not in NULLABLE_ORG_TABLES and table_name not in SPECIAL_RLS_TABLES:
                standard.add(table_name)

    return SELF_KEYED_TABLES | NULLABLE_ORG_TABLES | SPECIAL_RLS_TABLES | frozenset(standard)


def _collect_rls_covered_tables(versions_dir: Path) -> tuple[set[str], str]:
    """Parse all migration files and return (covered_table_names, combined_text).

    A table is considered covered if any migration file contains:
    - apply_rls_policy(op, "<table>")  (standard pattern)
    - apply_rls_policy_nullable_org(op, "<table>")  (nullable-org pattern)
    - apply_rls_policy_self_keyed(op, "<table>")  (self-keyed pattern)
    - ALTER TABLE <table> ENABLE ROW LEVEL SECURITY  (direct SQL)
    """
    covered: set[str] = set()
    all_text_parts: list[str] = []

    # Regex patterns for helper function calls
    helper_re = re.compile(
        r'apply_rls_policy(?:_nullable_org|_self_keyed)?\s*\(\s*op\s*,\s*["\']([\w]+)["\']'
    )
    # Regex for direct SQL ENABLE statements
    enable_re = re.compile(
        r'ALTER\s+TABLE\s+(\w+)\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY',
        re.IGNORECASE,
    )

    for migration_file in sorted(versions_dir.glob("*.py")):
        text = migration_file.read_text(encoding="utf-8")
        all_text_parts.append(text)
        for match in helper_re.finditer(text):
            covered.add(match.group(1))
        for match in enable_re.finditer(text):
            covered.add(match.group(1))

    return covered, "\n".join(all_text_parts)


def _check_organizations_self_keyed(all_migration_text: str) -> bool:
    """Verify organizations uses id = current_setting (not organization_id).

    Checks that apply_rls_policy_self_keyed is used for organizations,
    which guarantees the id-based (not organization_id-based) policy.
    """
    self_keyed_re = re.compile(
        r'apply_rls_policy_self_keyed\s*\(\s*op\s*,\s*["\']organizations["\']'
    )
    return bool(self_keyed_re.search(all_migration_text))


def main() -> int:
    """Run the RLS coverage check. Returns 0 on success, 1 on failure."""
    repo_root = Path(__file__).resolve().parent.parent
    versions_dir = repo_root / "alembic" / "versions"

    if not versions_dir.is_dir():
        print(f"ERROR: alembic/versions/ directory not found at {versions_dir}", file=sys.stderr)
        return 1

    # Collect all tables that need RLS
    all_rls_tables = _collect_all_rls_tables()

    # Collect tables covered by migrations
    covered_tables, all_migration_text = _collect_rls_covered_tables(versions_dir)

    # Find uncovered tables
    uncovered = all_rls_tables - covered_tables

    errors: list[str] = []

    if uncovered:
        sorted_uncovered = sorted(uncovered)
        errors.append(
            "The following tables need RLS but have no ENABLE ROW LEVEL SECURITY "
            "statement in any migration:\n"
            + "\n".join(f"  - {t}" for t in sorted_uncovered)
        )

    # Verify organizations uses id = current_setting (self-keyed), not organization_id
    if not _check_organizations_self_keyed(all_migration_text):
        errors.append(
            "Table 'organizations' must use apply_rls_policy_self_keyed() "
            "(id = current_setting pattern), not the standard organization_id pattern."
        )

    if errors:
        print("RLS COVERAGE CHECK FAILED\n", file=sys.stderr)
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    total = len(all_rls_tables)
    print(f"RLS coverage OK: {total} table(s) covered ({', '.join(sorted(all_rls_tables))})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
