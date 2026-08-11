.PHONY: help install lint typecheck test train clean

help: ## List available targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

install: ## Sync Python environment (uv) and install pre-commit hooks
	uv sync --group dev
	uv run pre-commit install

lint: ## Ruff format check + lint
	uv run ruff format --check .
	uv run ruff check .

typecheck: ## Mypy over solclear/ and tests/
	uv run mypy

test: ## Run the pytest suite (includes the honesty tests)
	uv run pytest

train: ## Regenerate the clearance model from the immutable snapshot matrix
	uv run python -m solclear.train

clean: ## Remove caches (never touches data/snapshots or solclear/artifacts)
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} +
