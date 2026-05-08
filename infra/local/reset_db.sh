#!/usr/bin/env bash
# Drop + recria o database. CUIDADO: apaga TUDO.
# Pede confirmação interativa.

set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ -f "$ROOT_DIR/.env" ]]; then
    # shellcheck disable=SC1091
    set -a; source "$ROOT_DIR/.env"; set +a
fi

PG_DB="${PG_DB:-climate_esg}"

echo "ATENÇÃO: isso vai DROP DATABASE \"$PG_DB\". Tem certeza? [yes/N]"
read -r confirm
[[ "$confirm" == "yes" ]] || { echo "abortado."; exit 1; }

sudo -u postgres psql -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS \"$PG_DB\";"
bash "$ROOT_DIR/infra/local/init_db.sh"
