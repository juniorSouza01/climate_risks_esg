# ADR-0002 — Stack local sem Docker no MVP

**Data:** 2026-05-07
**Status:** Aceito
**Decisor:** Osney Andrade de Souza Junior

## Contexto

O `docs/source/project.md` §11 define como critério de saída da F0 que `make up` traga a stack de pé via `docker-compose.yml` (Postgres+PostGIS, MinIO, Airflow). A §13 deixa a stack de nuvem como decisão pendente.

O usuário decidiu desenvolver o MVP **localmente, sem Docker e sem docker-compose**.

## Decisão

1. Postgres 16, PostGIS 3 e pgvector são instalados **nativamente** via apt.
2. O object store MinIO é **substituído pelo filesystem local** estruturado em `data/bronze/`, `data/silver/`, `data/gold/`. A interface dentro do código é encapsulada em `climate_esg.utils.storage` para permitir trocar para S3/MinIO sem refatorar pontos de uso.
3. Não há `docker-compose.yml`, Dockerfiles ou pasta `infra/docker/` no MVP.
4. Bootstrap está em `infra/local/` (scripts shell + SQL) e é invocado via `make setup-system` e `make db-init`.

## Justificativa

- Decisão do usuário, presumivelmente por simplicidade operacional / restrição de ambiente.
- Para um piloto N=2 com volume de dados moderado (dezenas de GB de CMIP6), a sobrecarga operacional do Docker não se justifica frente ao ganho marginal.
- Postgres nativo + filesystem local elimina ~50% dos pontos de falha de uma stack inicial.

## Consequências

- A reprodutibilidade entre máquinas fica menos hermética (versões exatas de libs do sistema, locale, timezone). Mitigação: scripts em `infra/local/` versionam comandos apt e versões mínimas; checagem de versão no `setup_postgres.sh`.
- Migração futura para Docker/Kubernetes na fase Beta/GA exigirá criar Dockerfiles e ajustar paths. Para minimizar dor: nada no código deve depender de paths absolutos; tudo via env vars (`DATA_BRONZE`, `DATABASE_URL`, etc.).
- CI no GitHub Actions ainda pode rodar Postgres como service container (isso é diferente de exigir Docker para dev local).

## Alternativas consideradas

- **AWS desde o dia 1:** rejeitado por custo e fricção em fase exploratória.
- **GCP:** mesmo motivo.
- **Docker apenas para Postgres:** rejeitado para manter consistência da decisão do usuário.

## Revisão

Reavaliar no fim da F2 (entrada na Beta), quando o piloto N=2 expandir para cobertura setorial e a operação multi-máquina vier à tona.
