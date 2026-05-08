# Bootstrap local

Scripts que substituem o `docker-compose.yml` que o `project.md` previa. Decisão registrada em [`../../docs/adrs/0002-no-docker-local.md`](../../docs/adrs/0002-no-docker-local.md).

| Script | O que faz | Quando rodar |
|---|---|---|
| `setup_postgres.sh` | Adiciona PGDG, instala Postgres 16 + PostGIS 3 + pgvector via apt | Uma única vez por máquina |
| `init_db.sh` | Cria role, database e extensões. Idempotente | Após `setup_postgres.sh` e a cada nova máquina |
| `reset_db.sh` | DROP + recria o database. Pede confirmação | Apenas em desenvolvimento, quando o esquema fica inconsistente |

Tudo é orquestrado pelo `Makefile` da raiz: `make setup-system`, `make db-init`, `make db-reset`.
