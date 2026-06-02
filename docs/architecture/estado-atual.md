# Estado Atual — Onde Estamos, Onde Queremos Chegar

> **Documento de status técnico.** Atualizado em 2026-06-01.
> Fonte de verdade do produto: [`docs/source/project.md`](../source/project.md) (v2.0). Desvios formalizados em [`docs/adrs/`](../adrs/).
> Este documento descreve o **estado real do código** (verificado contra o repositório), não a intenção.

---

## 1. Resumo executivo

O projeto está na **Fase F0 — Fundação**, com o **critério de saída ATINGIDO** (2026-06-01): ambiente provisionado, banco materializado e **execução end-to-end** de um dataset CMIP6 promovido de bronze até ouro com linhagem (`run_sk`), validada num ambiente real.

**Veredito:** F0 fechada. Próximo: F1 — MVP físico (índices xclim + score físico).

| Dimensão | Estado |
|---|---|
| Estrutura de repositório | ✅ Completa |
| Decisões de arquitetura (ADRs 1–5) | ✅ Documentadas |
| Parser/ingestão ESGF | ✅ Implementado e testado |
| Contrato de score (`ScoreBand`) | ✅ Implementado e testado |
| ORM do star schema | ✅ Modelado + migration `0001` aplicada |
| Pipeline bronze→prata→ouro | ✅ `fetch`/`validate`/`promote`/`materialize` + linhagem — **E2E validado** (45 arquivos → 1 Zarr → 1080 linhas em `fact_climate_indicator`) |
| Ambiente local (uv, venv, deps, Postgres+PostGIS) | ✅ Provisionado |
| Banco materializado (Alembic + seed) | ✅ `make db-migrate` + `db-seed` rodados |
| Gates de qualidade (ruff/mypy/pytest) | ✅ Verdes (`ruff` ok, `mypy` 0 erros, 23 testes) |
| CI (GitHub Actions) | 🟡 `ci.yml` escrito + gates passam localmente; falta primeiro push/validação no GH |
| Modelos de risco (físico/transição) | 🟡 Stubs (correto — são F1/F2) |

> **Marco 2026-06-01 — F0 fechada.** Smoke test E2E: `ingest_cmip6_flow(..., do_validate=True, do_promote=True, do_materialize=True)` → `{'fetched': 45, 'validated': 45, 'promoted': 1, 'indicator_rows': 1080}` (540 datas distintas 1970–2014, 2 ativos, 1 `run_sk`). Calendário `dim_date` cobre 1850–2100. Entregues no Sprint 1+2: Alembic + migration `0001`, `db/seed.py` + CLI `db seed`, pipeline completo (`validate_netcdf`/`promote_to_silver`/`materialize_indicators`), linhagem (`governance/lineage.py`), validação CF (`ingestion/cf_validation.py`), índices (`modeling/climate_indices.py`), CI + pre-commit.

---

## 2. O que JÁ existe e funciona (verificado no código)

### 2.1. Fundação de repositório
- **Monorepo** com layout por domínio: [`src/climate_esg/`](../../src/climate_esg), [`pipelines/`](../../pipelines), [`infra/local/`](../../infra/local), [`docs/`](..), [`tests/`](../../tests). Diretórios `src/r_analytics/` e `src/frontend/` existem (vazios — esperado).
- **5 ADRs aceitos** formalizando os desvios do `project.md`:
  - ADR-0001 — monorepo privado/proprietário.
  - ADR-0002 — stack local **sem Docker** (Postgres nativo + filesystem `data/bronze|silver|gold`).
  - ADR-0003 — **Prefect 3** no lugar de Airflow.
  - ADR-0004 — piloto **N=2 (Döhler + Schulz)** com **soma ponderada** no lugar de XGBoost no MVP.
  - ADR-0005 — perfil de hazard centrado em **Joinville/SC**; plano de expansão de variáveis CMIP6.
- `pyproject.toml` com dependências reais (xarray, dask, geopandas, xclim, SQLAlchemy 2, FastAPI, Prefect 3, MLflow…), gerenciado por **uv**. Lint (ruff), tipos (mypy strict) e pytest configurados com marcadores `slow`/`integration`/`needs_data`.
- `Makefile` com alvos (`install-dev`, `setup-system`, `db-init`, `db-migrate`, `prefect-server`, `api`, `check`, `test-cov`).
- `README.md` com aviso proprietário e quick start.

### 2.2. Ingestão ESGF/CMIP6 — **implementação real**
[`src/climate_esg/ingestion/esgf_client.py`](../../src/climate_esg/ingestion/esgf_client.py):
- `parse_wget_script` / `parse_wget_directory`: extraem o manifesto (filename, url, checksum, tipo) dos scripts wget do MetaGrid, **sem executar shell**.
- `CMIP6Identifier.from_filename`: decompõe o nome CF (`variable_table_source_experiment_member_grid_period.nc`).
- `ESGFManifest`: helpers `by_variable`, `variables`, `members`, `experiments`.
- Download assíncrono `download_manifest_async` com **httpx + asyncio**, concorrência limitada por semáforo, **validação de checksum SHA256**, **retry exponencial** (tenacity) e **idempotência** (pula arquivo já válido).
- Coberto por [`tests/unit/test_esgf_parser.py`](../../tests/unit/test_esgf_parser.py) rodando contra os **10 scripts wget reais** (450 entradas `.nc`).

### 2.3. Contrato de score — `ScoreBand`
[`src/climate_esg/modeling/scoring.py`](../../src/climate_esg/modeling/scoring.py):
- `ScoreBand(central, low, high)` com validação `0 ≤ low ≤ central ≤ high ≤ 100` — materializa o princípio **"score é faixa, nunca ponto"** (§2.2.4).
- `compose_score` (combinação linear ponderada de bandas). Coberto por [`tests/unit/test_scoring.py`](../../tests/unit/test_scoring.py).

### 2.4. Modelagem dimensional (ORM)
[`src/climate_esg/db/models.py`](../../src/climate_esg/db/models.py) — SQLAlchemy 2.x:
- Dimensões: `dim_company` (SCD2), `dim_asset` (PostGIS POINT), `dim_region` (MULTIPOLYGON), `dim_date`, `dim_scenario`, `dim_climate_variable`, `dim_model_run`.
- Fatos: `fact_climate_indicator`, `fact_physical_risk_score`, `fact_transition_risk_score`.
- **Toda fato carrega `run_sk`** (princípio de auditabilidade §2.2.2).
- `db/base.py`: engine, `session_scope`, `Base` declarativa.

### 2.5. Demais peças de fundação
- `config.py`: settings via pydantic-settings (`.env`), URL SQLAlchemy derivada.
- `utils/storage.py`: abstração do data lake local (`Layer` bronze/prata/ouro, layout DRS CMIP6) — isola filesystem hoje, S3/MinIO amanhã.
- `cli/main.py`: CLI Typer `climate-esg manifests inspect`.
- `api/main.py`: FastAPI com `/health` e `/version`.
- `pipelines/flows/ingest_cmip6.py`: flow Prefect com a task `fetch_manifest` **funcional**.

---

## 3. O que está STUB / pendente (gaps da F0)

| # | Gap | Onde | Impacto |
|---|---|---|---|
| 1 | **Ambiente não provisionado** — `uv` não instalado; sem `.venv` nem `uv.lock`. Há `python3.12` (não `3.11`, mas o `uv` resolve). | máquina local | Nada Python roda hoje. |
| 2 | **Banco não materializado** — sem `alembic.ini` nem `migrations/`. `make db-migrate` falha. As tabelas do ORM **nunca foram criadas**. | `src/climate_esg/db/` | Sem schema físico, nenhuma fato/dimensão persiste. |
| 3 | **Postgres não inicializado** — serviço online, mas role `climate_esg` não autentica. `init_db.sh` exige `sudo` interativo. | `infra/local/init_db.sh` | Conexão falha. |
| 4 | **Pipeline incompleto** — `validate_netcdf` e `promote_to_silver` são `NotImplementedError`. | [`ingest_cmip6.py`](../../pipelines/flows/ingest_cmip6.py) | **Bronze→prata→ouro não fecha** — é o coração do critério de saída da F0. |
| 5 | **Nenhum NetCDF baixado** — `data/bronze/` vazio. | `data/bronze/` | Sem dado, não há smoke test. |
| 6 | **Sem CI** — não há `.github/workflows/`. | repo | F0 pede "CI verde". |
| 7 | **Seed de dimensões ausente** — sem `db/seed.py`; `dim_scenario`, `dim_climate_variable`, `dim_company` (Döhler/Schulz), `dim_asset` (plantas em Joinville) vazias. | `src/climate_esg/db/` | Pipeline não tem chaves para escrever fatos. |

---

## 4. Critério de saída da F0 (adaptado pelos ADRs)

O `project.md` §11 define: *"`make up` traz a stack de pé; ingestão de 1 NetCDF de teste promovido até ouro."*
Ajustado pelos ADRs 0002/0003 (sem Docker, Prefect):

> **F0 fecha quando:** `make setup-system && make db-init && make db-migrate` materializam o banco; `make install-dev` provisiona o venv; e `climate-esg`/flow Prefect ingere **1 NetCDF `tasmin` historical** → valida CF → promove a Zarr na prata → materializa ≥1 indicador climático em `fact_climate_indicator` (ouro), com `run_sk` registrado em `dim_model_run`. CI verde no GitHub Actions.

Hoje faltam os itens 1–7 da seção 3 para atingir isso.

---

## 5. Onde queremos chegar

### 5.1. Visão do produto
Plataforma **auditável** de risco climático **físico** e de **transição** por empresa/região, alinhada a TCFD, ISSB IFRS S2 e cenários NGFS/IPCC, para investidores institucionais. Score sempre como **banda de incerteza**, sempre com **linhagem** (`run_sk` → commit + dado + parâmetros).

### 5.2. Escopo do MVP (16 semanas), já reconciliado com os ADRs
- **Empresas:** N=2 — **Döhler** (têxtil, capital fechado) e **Schulz** (autopeças/compressores, B3 SHUL3/SHUL4), ambas em **Joinville/SC**. *(ADR-0004 — diverge do agronegócio B3 do doc.)*
- **Hazards prioritários:** enchentes, deslizamentos, ventos extremos, calor extremo urbano. *(ADR-0005)*
- **Cenários:** histórico (temos) + SSP2-4.5 + SSP5-8.5 (**a baixar**).
- **Horizontes:** 2030 / 2040 / 2050.
- **Risco físico:** soma ponderada de indicadores xclim normalizados (determinístico).
- **Risco de transição:** **soma ponderada calibrada** (NÃO XGBoost no MVP — ADR-0004; XGBoost só na F3).
- **Dashboard:** estático — heatmap de carteira, drill-down por empresa, mapa de ativos com hazards. Sem agente conversacional.

### 5.3. Roadmap
| Fase | Duração | Entregável-chave | Critério de saída |
|---|---|---|---|
| **F0 — Fundação** | 3 sem | Banco materializado + pipeline E2E + CI | 1 NetCDF bronze→ouro; CI verde |
| **F1 — MVP físico** | 6 sem | Ingestão CMIP6 completa (`pr`,`tasmax`,`sfcWindmax` × SSP) + índices xclim + score físico + mapa | Score físico reproduzível; dashboard navegável |
| **F2 — MVP transição** | 5 sem | Coletor CDP/CVM + soma ponderada de transição + SHAP/explicação + score composto | Score composto com banda |
| **F3 — Beta** | 12 sem | Expansão setorial, RAG, score regional, XGBoost, piloto com investidor | Adoção mensurada |
| **F4 — GA** | 16 sem | Agente conversacional, SSO/RBAC, observabilidade | Lançamento comercial |

---

## 6. Princípios não negociáveis (lembrete operacional)

1. **Modelos calculam, LLM só comunica/extrai.** Nenhum score numérico final vem de LLM.
2. **Tudo auditável.** Nenhuma fato sem `run_sk`. Recalibração gera nova linha, nunca update.
3. **Reprodutibilidade.** Dado versionado + código versionado + ambiente versionado.
4. **Banda de incerteza explícita.** `ScoreBand(central, low, high)`.
5. **Comece simples.** Soma ponderada → XGBoost → redes → foundation models, só com ganho mensurável.

---

## 7. Próximos passos imediatos (entrada para o backlog)

Ver [`docs/planning/backlog-sprints.md`](../planning/backlog-sprints.md). Em ordem de desbloqueio:
1. Provisionar ambiente (`uv`, venv, deps) e inicializar Postgres.
2. Configurar **Alembic** + migration inicial do star schema.
3. `db/seed.py` com cenários, variáveis CF e as 2 empresas + ativos em Joinville.
4. Implementar `validate_netcdf` e `promote_to_silver` (xarray + cf-xarray + Zarr + xclim).
5. CI no GitHub Actions (ruff + mypy + pytest, Postgres como service container).
6. **Smoke test E2E** que fecha a F0.
