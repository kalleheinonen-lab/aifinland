.PHONY: install lint typecheck test check-rls build ci \
        ci-api ci-web

# ---------------------------------------------------------------------------
# Root database layer targets
# ---------------------------------------------------------------------------

install:
	pip install -e '.[dev]'

lint:
	python -m ruff check .

typecheck:
	python -m mypy src/

test:
	python -m pytest -m 'not slow'

check-rls:
	python scripts/check_rls_coverage.py

build:
	@echo 'no build artifact'

# ---------------------------------------------------------------------------
# apps/api targets
# ---------------------------------------------------------------------------

ci-api:
	@echo "--- CI: apps/api ---"
	cd apps/api && pip install --quiet -r requirements.txt
	cd apps/api && python -m ruff check .
	cd apps/api && python -m mypy src/
	cd apps/api && python -m pytest

# ---------------------------------------------------------------------------
# apps/web targets
# ---------------------------------------------------------------------------

ci-web:
	@echo "--- CI: apps/web ---"
	pnpm install --frozen-lockfile
	cd apps/web && npx oxlint .
	cd apps/web && npx tsc --noEmit
	cd apps/web && npx vitest run

# ---------------------------------------------------------------------------
# AC-10 [e2e]: WHEN make ci executes against the complete codebase THE SYSTEM
# SHALL pass lint, typecheck, all tests, and the RLS coverage gate end-to-end
# with nothing mocked.
#
# Orchestrates: root DB layer → apps/api → apps/web
# ---------------------------------------------------------------------------

ci: install lint typecheck test check-rls build ci-api ci-web
	@echo "CI passed (root DB + apps/api + apps/web)"
