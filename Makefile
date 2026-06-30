SHELL := /bin/bash
.DEFAULT_GOAL := help

# Configuráveis (sobrescreva no .env ou exporte na shell)
PG_USER       ?= climate_esg
PG_DB         ?= climate_esg
PG_HOST       ?= localhost
PG_PORT       ?= 5432
PYTHON        ?= python3.11
UV            ?= uv
API_PORT      ?= 8001

# ---- Help ----------------------------------------------------------------
.PHONY: help
help: ## Lista alvos disponíveis
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ---- Setup ---------------------------------------------------------------
.PHONY: install install-dev install-nlp
install: ## Instala dependências de produção via uv
	$(UV) sync --no-dev

install-dev: ## Instala dependências dev (ruff/mypy/pytest)
	$(UV) sync --extra dev

install-nlp: ## Adiciona o extras NLP (transformers, torch, etc.)
	$(UV) sync --extra dev --extra nlp

.PHONY: setup-system
setup-system: ## Instala Postgres+PostGIS+pgvector via apt (Ubuntu/Mint)
	bash infra/local/setup_postgres.sh

# ---- Banco de dados ------------------------------------------------------
.PHONY: db-init db-migrate db-seed db-reset db-shell
db-init: ## Cria role/db e habilita extensões (postgis, pgvector)
	bash infra/local/init_db.sh

db-migrate: ## Aplica migrations Alembic (alembic upgrade head)
	$(UV) run alembic upgrade head

db-seed: ## Popula dimensões-base (cenários, variáveis, empresas, ativos, datas)
	$(UV) run climate-esg db seed

db-reset: ## DROP + recria database (CUIDADO em prod)
	bash infra/local/reset_db.sh

db-shell: ## Abre psql no database
	psql -h $(PG_HOST) -p $(PG_PORT) -U $(PG_USER) -d $(PG_DB)

# ---- Pipelines (Prefect 3) ----------------------------------------------
.PHONY: scores prefect-server prefect-worker
scores: ## Recalcula scores (exposição/físico/transição/composto/explicação/financeiro) sem Prefect
	$(UV) run python -m pipelines.flows.compute_scores

prefect-server: ## Sobe Prefect server local em :4200
	$(UV) run prefect server start

prefect-worker: ## Worker padrão na work pool 'default'
	$(UV) run prefect worker start --pool default --type process

# ---- Qualidade -----------------------------------------------------------
.PHONY: lint format typecheck test test-cov check
lint: ## ruff check
	$(UV) run ruff check src tests pipelines

format: ## ruff format
	$(UV) run ruff format src tests pipelines

typecheck: ## mypy strict em src/climate_esg
	$(UV) run mypy

test: ## pytest rápido (exclui slow/integration/needs_data)
	$(UV) run pytest -m "not slow and not integration and not needs_data"

test-cov: ## pytest com cobertura
	$(UV) run pytest --cov --cov-report=term-missing --cov-report=html

check: lint typecheck test ## CI local: lint + types + tests

# ---- Docker (stack completa) ---------------------------------------------
.PHONY: up down logs build-images
up: ## Sobe db+api+frontend via docker compose (build na 1ª vez)
	docker compose up --build

down: ## Derruba a stack (mantém volume do banco)
	docker compose down

logs: ## Segue os logs da stack
	docker compose logs -f

build-images: ## Builda as imagens sem subir
	docker compose build

# ---- API / Frontend ------------------------------------------------------
.PHONY: api frontend
api: ## Sobe FastAPI em :$(API_PORT)
	$(UV) run uvicorn climate_esg.api.main:app --reload --host 0.0.0.0 --port $(API_PORT)

frontend: ## Sobe Vite dev server (depois de F1)
	cd src/frontend && npm run dev

# ---- Limpeza -------------------------------------------------------------
.PHONY: clean
clean: ## Remove caches Python
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage coverage.xml
