.DEFAULT_GOAL := help
BACKEND := backend
FRONTEND := frontend

.PHONY: help install dev-api dev-web migrate lint format typecheck test openapi requirements check-requirements check

help: ## List targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "%-20s %s\n", $$1, $$2}'

install: ## Install backend and frontend dependencies
	cd $(BACKEND) && uv sync
	cd $(FRONTEND) && npm ci

dev-api: ## Run the API with reload on :8000
	cd $(BACKEND) && uv run uvicorn --factory app.main:create_app --reload --port 8000

dev-web: ## Run the frontend on :5173 (calls the API on :8000)
	cd $(FRONTEND) && npm run dev

migrate: ## Apply database migrations
	cd $(BACKEND) && uv run python -m app.db migrate

lint: ## ruff lint + format check; eslint + prettier
	cd $(BACKEND) && uv run ruff check . && uv run ruff format --check .
	cd $(FRONTEND) && npm run lint

format: ## ruff fix + format; eslint fix + prettier
	cd $(BACKEND) && uv run ruff check --fix . && uv run ruff format .
	cd $(FRONTEND) && npm run format

typecheck: ## mypy strict; tsc
	cd $(BACKEND) && uv run mypy app tests
	cd $(FRONTEND) && npm run typecheck

test: ## pytest; vitest
	cd $(BACKEND) && uv run pytest --cov=app --cov-report=term
	cd $(FRONTEND) && npm test

openapi: ## Export the API's OpenAPI document and regenerate the frontend client
	cd $(BACKEND) && uv run python -m app.export_openapi > ../$(FRONTEND)/openapi.json
	cd $(FRONTEND) && npm run openapi

requirements: ## Regenerate the pip requirements files from uv.lock
	cd $(BACKEND) && uv export --no-dev --no-emit-project --no-hashes -q > requirements.txt
	cd $(BACKEND) && uv export --no-emit-project --no-hashes -q > requirements-dev.txt

check-requirements: ## Fail if the requirements files drift from uv.lock
	cd $(BACKEND) && uv lock --check && \
	  uv export --no-dev --no-emit-project --no-hashes -q | diff -q - requirements.txt && \
	  uv export --no-emit-project --no-hashes -q | diff -q - requirements-dev.txt

check: lint typecheck test check-requirements ## Everything CI runs
