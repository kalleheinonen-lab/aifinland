"""AC-10 [e2e] smoke test: verify that `make ci` exits with code 0.

AC-10 [e2e]: WHEN `make ci` executes against the complete codebase THE SYSTEM
SHALL pass lint, typecheck, all tests, and the RLS coverage gate end-to-end
with nothing mocked.

This test is the persisted, repeatable verification of AC-10. It shells out to
`make ci` and asserts exit code 0, ensuring the contract is enforced on every
CI run and cannot silently regress.

Note: This test is intentionally marked with `pytest.mark.slow` so it can be
skipped during fast inner-loop development (`pytest -m "not slow"`). The GitHub
CI workflow runs it unconditionally via the `quality-db` job which invokes
`make ci` directly, providing the authoritative e2e gate.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

# Repo root is two levels up from this file (tests/test_ci_smoke.py)
_REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.slow
def test_ac10_make_ci_exits_zero() -> None:
    """AC-10 [e2e]: `make ci` must exit 0 against the complete codebase.

    Exercises: root DB layer (lint, typecheck, pytest, RLS gate) +
               apps/api (ruff, mypy, pytest) +
               apps/web (oxlint, tsc, vitest).
    Nothing is mocked -- this is the real end-to-end build gate.
    """
    # AC-10: expect exit code 0 from `make ci` on the complete codebase
    result = subprocess.run(
        ["make", "ci"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"`make ci` failed with exit code {result.returncode}.\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
