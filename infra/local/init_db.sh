#!/usr/bin/env bash
# Cria role/database para o climate_esg e habilita extensões.
# Idempotente: pode rodar várias vezes sem erro.
#
# Uso:
#   bash infra/local/init_db.sh
#
# Variáveis (defaults via .env / Makefile):
#   PG_USER (default: climate_esg)
#   PG_PASSWORD (default: changeme_local_only)
#   PG_DB (default: climate_esg)

set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ -f "$ROOT_DIR/.env" ]]; then
    # shellcheck disable=SC1091
    set -a; source "$ROOT_DIR/.env"; set +a
fi

PG_USER="${PG_USER:-climate_esg}"
PG_PASSWORD="${PG_PASSWORD:-changeme_local_only}"
PG_DB="${PG_DB:-climate_esg}"

run_sql() {
    sudo -u postgres psql -v ON_ERROR_STOP=1 -d "$1" -c "$2"
}

echo "==> Criando role $PG_USER (se não existir)"
sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${PG_USER}'" \
  | grep -q 1 \
  || run_sql postgres "CREATE ROLE ${PG_USER} LOGIN PASSWORD '${PG_PASSWORD}';"

echo "==> Garantindo permissões de criação"
run_sql postgres "ALTER ROLE ${PG_USER} CREATEDB;"

echo "==> Criando database $PG_DB (se não existir)"
sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${PG_DB}'" \
  | grep -q 1 \
  || sudo -u postgres createdb -O "$PG_USER" "$PG_DB"

echo "==> Habilitando extensões em $PG_DB"
run_sql "$PG_DB" "CREATE EXTENSION IF NOT EXISTS postgis;"
run_sql "$PG_DB" "CREATE EXTENSION IF NOT EXISTS postgis_topology;"
run_sql "$PG_DB" "CREATE EXTENSION IF NOT EXISTS vector;"
run_sql "$PG_DB" "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
run_sql "$PG_DB" "CREATE EXTENSION IF NOT EXISTS btree_gin;"

echo "==> Concedendo privilégios"
run_sql "$PG_DB" "GRANT ALL ON SCHEMA public TO ${PG_USER};"
run_sql "$PG_DB" "ALTER SCHEMA public OWNER TO ${PG_USER};"

echo "==> Verificação"
PGPASSWORD="$PG_PASSWORD" psql \
    -h "${PG_HOST:-localhost}" -p "${PG_PORT:-5432}" \
    -U "$PG_USER" -d "$PG_DB" \
    -c "SELECT extname, extversion FROM pg_extension ORDER BY extname;"

echo
echo "OK. Database $PG_DB pronto para receber migrations."
echo "Próximo (depois das migrations Alembic):  make db-migrate"
