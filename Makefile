.DEFAULT_GOAL := help
BACKEND := backend
# Agent hooks, linted and typed with the backend rules.
HOOKS := ../.claude/hooks
FRONTEND := frontend

.PHONY: help install dev-api dev-web migrate lint format typecheck test build openapi openapi-drift pre-commit requirements check-requirements check check-backend check-frontend \
	lint-backend lint-frontend typecheck-backend typecheck-frontend test-backend test-frontend

help: ## List targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "%-20s %s\n", $$1, $$2}'

install: ## Install backend and frontend dependencies and the git pre-commit hook
	cd $(BACKEND) && uv sync
	cd $(FRONTEND) && npm ci
	uv run --project $(BACKEND) pre-commit install

dev-api: ## Run the API with reload on :8000
	cd $(BACKEND) && uv run uvicorn --factory app.main:create_app --reload --port 8000

dev-web: ## Run the frontend on :5173 (calls the API on :8000)
	cd $(FRONTEND) && npm run dev

migrate: ## Apply database migrations
	cd $(BACKEND) && uv run python -m app.db migrate

lint: lint-backend lint-frontend ## ruff lint + format check; eslint + prettier

lint-backend:
	cd $(BACKEND) && uv run ruff check . $(HOOKS) && uv run ruff format --check . $(HOOKS)

lint-frontend:
	cd $(FRONTEND) && npm run lint

format: ## ruff fix + format; eslint fix + prettier
	cd $(BACKEND) && uv run ruff check --fix . $(HOOKS) && uv run ruff format . $(HOOKS)
	cd $(FRONTEND) && npm run format

typecheck: typecheck-backend typecheck-frontend ## mypy strict; tsc

typecheck-backend:
	cd $(BACKEND) && uv run mypy app tests $(HOOKS)/format.py

typecheck-frontend:
	cd $(FRONTEND) && npm run typecheck

test: test-backend test-frontend ## pytest; vitest

test-backend:
	cd $(BACKEND) && uv run pytest --cov=app --cov-report=term

test-frontend:
	cd $(FRONTEND) && npm test

build: ## Production build of the frontend
	cd $(FRONTEND) && npm run build

openapi: ## Export the API's OpenAPI document and regenerate the frontend client
	cd $(BACKEND) && uv run python -m app.export_openapi > ../$(FRONTEND)/openapi.json
	cd $(FRONTEND) && npm run openapi

requirements: ## Regenerate the pip requirements files from uv.lock
	cd $(BACKEND) && uv export --no-dev --no-emit-project --no-hashes --no-header -q > requirements.txt
	cd $(BACKEND) && uv export --no-emit-project --no-hashes --no-header -q > requirements-dev.txt

pre-commit: ## Run every pre-commit hook on all files
	uv run --project $(BACKEND) pre-commit run --all-files

openapi-drift: ## Fail if the committed OpenAPI document or generated client is stale
	$(MAKE) openapi
	git diff --exit-code -- $(FRONTEND)/openapi.json $(FRONTEND)/src/api/generated
	@untracked=$$(git ls-files --others --exclude-standard -- $(FRONTEND)/src/api/generated); \
	  if [ -n "$$untracked" ]; then echo "untracked generated files:"; echo "$$untracked"; exit 1; fi

check-requirements: ## Fail if the requirements files drift from uv.lock
	cd $(BACKEND) && uv lock --check && \
	  uv export --no-dev --no-emit-project --no-hashes --no-header -q | diff -q - requirements.txt && \
	  uv export --no-emit-project --no-hashes --no-header -q | diff -q - requirements-dev.txt

# CI (.github/workflows/ci.yml) runs these same targets, one job per group.
check-backend: lint-backend typecheck-backend test-backend check-requirements
check-frontend: lint-frontend typecheck-frontend test-frontend build

check: check-backend check-frontend openapi-drift ## Everything CI runs
