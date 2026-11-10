.DEFAULT_GOAL := help
BACKEND := backend

.PHONY: help install dev-api migrate lint format typecheck test requirements check-requirements check

help: ## List targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "%-20s %s\n", $$1, $$2}'

install: ## Install backend dependencies
	cd $(BACKEND) && uv sync

dev-api: ## Run the API with reload on :8000
	cd $(BACKEND) && uv run uvicorn --factory app.main:create_app --reload --port 8000

migrate: ## Apply database migrations
	cd $(BACKEND) && uv run python -m app.db migrate

lint: ## ruff lint + format check
	cd $(BACKEND) && uv run ruff check . && uv run ruff format --check .

format: ## ruff fix + format
	cd $(BACKEND) && uv run ruff check --fix . && uv run ruff format .

typecheck: ## mypy strict
	cd $(BACKEND) && uv run mypy app tests

test: ## pytest
	cd $(BACKEND) && uv run pytest --cov=app --cov-report=term

requirements: ## Regenerate the pip requirements files from uv.lock
	cd $(BACKEND) && uv export --no-dev --no-emit-project --no-hashes -q > requirements.txt
	cd $(BACKEND) && uv export --no-emit-project --no-hashes -q > requirements-dev.txt

check-requirements: ## Fail if the requirements files drift from uv.lock
	cd $(BACKEND) && uv lock --check && \
	  uv export --no-dev --no-emit-project --no-hashes -q | diff -q - requirements.txt && \
	  uv export --no-emit-project --no-hashes -q | diff -q - requirements-dev.txt

check: lint typecheck test check-requirements ## Everything CI runs
