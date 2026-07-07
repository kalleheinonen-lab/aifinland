.PHONY: install lint typecheck test check-rls build ci

install:
	pip install -e '.[dev]'

lint:
	ruff check .

typecheck:
	mypy src/

test:
	pytest

check-rls:
	python scripts/check_rls_coverage.py

build:
	@echo 'no build artifact'

ci: install lint typecheck test check-rls build
	@echo "CI passed"
