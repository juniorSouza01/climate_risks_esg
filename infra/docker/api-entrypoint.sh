#!/usr/bin/env bash
set -euo pipefail

echo "==> Alembic upgrade head"
uv run alembic upgrade head

echo "==> Seed das dimensões-base"
uv run climate-esg db seed

echo "==> Subindo API em :8001"
exec uv run uvicorn climate_esg.api.main:app --host 0.0.0.0 --port 8001
