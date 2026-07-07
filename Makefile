.PHONY: install lint typecheck test build ci

install:
	cd apps/web && pnpm install
	cd apps/api && pip install -r requirements.txt

lint:
	cd apps/web && pnpm run lint
	cd apps/api && python -m ruff check .

typecheck:
	cd apps/web && pnpm run typecheck
	cd apps/api && python -m mypy src/app/

test:
	cd apps/web && pnpm run test
	cd apps/api && pytest

build:
	cd apps/web && pnpm run build
	cd apps/api && echo 'no build step'

ci: install lint typecheck test build
	@echo "CI passed"
