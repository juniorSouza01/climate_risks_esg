#!/usr/bin/env bash
# Instala Postgres 16 + PostGIS 3 + pgvector nativos no Ubuntu/Mint.
# Não roda init do database — isso é responsabilidade do init_db.sh.
#
# ADR-0002: stack local sem Docker.
#
# Uso: bash infra/local/setup_postgres.sh

set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
    echo "ERRO: este script só foi testado em Linux." >&2
    exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
    echo "ERRO: apt-get não disponível. Distros não-Debian precisam de adaptação." >&2
    exit 1
fi

PG_VERSION="${PG_VERSION:-16}"

echo "==> Habilitando o repositório PostgreSQL oficial (PGDG)"
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg lsb-release

if [[ ! -f /etc/apt/keyrings/postgresql.gpg ]]; then
    sudo install -d -m 0755 /etc/apt/keyrings
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
      | sudo gpg --dearmor -o /etc/apt/keyrings/postgresql.gpg
fi

# Detecta nome de release (Linux Mint reporta seu próprio codename; mapear p/ Ubuntu base)
CODENAME="$(lsb_release -cs)"
case "$CODENAME" in
    wilma|virginia|victoria|vanessa|una|uma) CODENAME="noble" ;;  # Mint 22+ → noble
    vera|vera|tara|tessa|ulyana|ulyssa) CODENAME="jammy" ;;       # Mint 21.x → jammy
esac

REPO_LINE="deb [signed-by=/etc/apt/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt ${CODENAME}-pgdg main"
echo "$REPO_LINE" | sudo tee /etc/apt/sources.list.d/pgdg.list >/dev/null
sudo apt-get update -qq

echo "==> Instalando Postgres $PG_VERSION + PostGIS + pgvector"
sudo apt-get install -y --no-install-recommends \
    "postgresql-${PG_VERSION}" \
    "postgresql-client-${PG_VERSION}" \
    "postgresql-contrib-${PG_VERSION}" \
    "postgresql-${PG_VERSION}-postgis-3" \
    "postgresql-${PG_VERSION}-postgis-3-scripts" \
    "postgresql-${PG_VERSION}-pgvector"

echo "==> Verificando serviço"
sudo systemctl enable --now "postgresql@${PG_VERSION}-main" || sudo systemctl enable --now postgresql

echo "==> Versões instaladas:"
psql --version
sudo -u postgres psql -c "SELECT version();" | head -3

cat <<'EOF'

OK. Postgres + PostGIS + pgvector instalados.

Próximo passo:
    bash infra/local/init_db.sh

Isso cria role, database e habilita as extensões.
EOF
