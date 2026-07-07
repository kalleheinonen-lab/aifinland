.PHONY: install lint typecheck test build ci

install:
	pip install -e '.[dev]'

lint:
	ruff check .

typecheck:
	mypy src/

test:
	pytest

build:
	@echo 'no build artifact'

ci: install lint typecheck test build
	@echo "CI passed"
