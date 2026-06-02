# Entregáveis & Gaps — O Que Falta Para Finalizar o Projeto

> Cruzamento do [`project.md`](../source/project.md) (v2.0) com o **código real** do repositório (verificado em 2026-06-01).
> Reconciliado com [ADRs 0001–0005](../adrs/). Complementa [`estado-atual.md`](../architecture/estado-atual.md).
>
> **Legenda de status:** ✅ pronto · 🟡 parcial/stub · ❌ ausente · 🔵 fora do MVP (Beta/GA).
> **Legenda de fase:** F0 Fundação · F1 físico · F2 transição · F3 Beta · F4 GA.

---

## Mapa rápido (visão de uma página)

| # | Entregável | Status | Fase-alvo |
|---|---|---|---|
| **D1** | Fundação, ambiente e banco | 🟡 | F0 |
| **D2** | CI/CD e qualidade | ❌ | F0 |
| **D3** | Ingestão ESGF/CMIP6 (pipeline E2E) | 🟡 | F0→F1 |
| **D4** | Armazenamento / lakehouse (prata/ouro, catálogo) | 🟡 | F1 |
| **D5** | Geoespacial (raster, exposição, regridding) | ❌ | F1 |
| **D6** | Modelagem física (índices + score) | 🟡 | F1 |
| **D7** | Modelagem de transição (soma ponderada) | 🟡 | F2 |
| **D8** | Impacto financeiro (DCF/VaR) | ❌ | F2/F3 |
| **D9** | Ingestão financeira/ESG/notícias | ❌ | F2 |
| **D10** | NLP (extração, classificação, RAG) | ❌ | F2/F3 |
| **D11** | Governança, auditoria, MLOps | 🟡 | F1+ |
| **D12** | API FastAPI v1 | 🟡 | F1/F2 |
| **D13** | Dashboard React | ❌ | F1/F2 |
| **D14** | R analytics (validação independente) | ❌ | F2/F3 |
| **D15** | Capacidades Beta/GA (RAG, agente, SSO, IaC) | 🔵 | F3/F4 |

---

## D1 — Fundação, ambiente e banco *(F0)*
**Pronto:** monorepo estruturado; `pyproject.toml`/uv; `Makefile`; ADRs 1–5; `config.py`; `utils/storage.py`; ORM do star schema ([`db/models.py`](../../src/climate_esg/db/models.py)); `db/base.py`; scripts `infra/local/*`. **✏️ Escrito (não validado):** Alembic completo + migration `0001`; `db/seed.py` + CLI `db seed`; alvos `db-migrate`/`db-seed`.

**Falta:**
- [ ] Provisionar ambiente: instalar `uv`, criar `.venv`, `uv sync --extra dev`, gerar `uv.lock`. *(precisa rede)*
- [ ] Inicializar Postgres (rodar `infra/local/setup_postgres.sh` + `init_db.sh` com sudo); role/extensões (postgis, vector, pg_trgm). *(precisa sudo)*
- [x] **Alembic**: `alembic.ini` + `migrations/env.py` + migration inicial do ORM. ✏️ escrito — validar com `make db-migrate`.
- [x] **`db/seed.py`**: `dim_scenario`, `dim_climate_variable`, `dim_company` (Döhler/Schulz), `dim_asset` (Joinville), `dim_date`. ✏️ escrito — validar com `make db-seed`. ⚠️ coords dos ativos são aproximadas (refinar em F1); LEI/CNPJ nulos (US 6.1.1).
- [ ] `.env` real a partir de `.env.example`.

## D2 — CI/CD e qualidade *(F0)*
**Pronto:** ruff + mypy strict + pytest configurados no `pyproject.toml`; marcadores `slow`/`integration`/`needs_data`; 2 suítes de teste unit. **✏️ Escrito (não validado):** `ci.yml` + `.pre-commit-config.yaml`.

**Falta:**
- [x] `.github/workflows/ci.yml`: ruff + mypy + pytest com **Postgres+PostGIS como service container**, aplicando migration e seed. ✏️ escrito — validar no primeiro push.
- [x] `.pre-commit-config.yaml` (ruff/ruff-format/mypy + hooks básicos). ✏️ escrito — `uv run pre-commit install`.
- [ ] Cobertura mínima como gate (hoje só `--cov-report`, sem `--cov-fail-under`).
- [ ] (Beta+) build/sign de artefatos, Trivy, lintr (R), ESLint (frontend).

## D3 — Ingestão ESGF/CMIP6 — pipeline E2E *(F0→F1)*
**Pronto:** parser wget + download async com checksum/retry/idempotência ([`esgf_client.py`](../../src/climate_esg/ingestion/esgf_client.py)) — **testado contra 10 scripts reais (450 arquivos)**; task `fetch_manifest` do flow Prefect.

**Falta:**
- [ ] Implementar `validate_netcdf` (abrir com xarray + cf-xarray, checar variável/unidade/dims CF, ranges físicos). Hoje `NotImplementedError`.
- [ ] Implementar `promote_to_silver` (regrid p/ grade comum, recorte espacial SC/Brasil, escrita **Zarr** com Zstd). Hoje `NotImplementedError`.
- [ ] `intake-esm`: gerar catálogo da prata; modelos consomem por catálogo, não por path.
- [ ] **Baixar 1 NetCDF `tasmin` historical** para o smoke test (fecha F0).
- [ ] **(F1)** Nova requisição MetaGrid: `pr`, `tasmax`, `sfcWindmax` × `historical+ssp245+ssp585`, prefixo `v2_` (ADR-0005).
- [ ] **(F1)** Ingestão em lote da v2 + deployment/schedule Prefect.

## D4 — Armazenamento / lakehouse *(F1)*
**Pronto:** layout bronze/prata/ouro local; abstração `storage.py`; star schema modelado no ORM.

**Falta:**
- [ ] Materializar prata (Zarr) e ouro (Parquet + tabelas Postgres) de fato.
- [ ] Fatos ainda não modeladas no ORM: `fact_hazard_exposure`, `fact_score_explanation`, `fact_news_signal` (F1/F2).
- [ ] Particionamento de `fact_climate_indicator` por `scenario_sk`/ano.
- [ ] Índice GIST em `dim_region.geom` / `dim_asset.geom` (via migration).
- [ ] **(Beta)** pgvector: tabelas `documents`/`doc_chunks` + índice HNSW.

## D5 — Geoespacial *(F1)*
**Pronto:** nada além do diretório `geospatial/` vazio.

**Falta:**
- [ ] `raster_ops.py` (reamostragem, recorte, CRS via rioxarray/rasterio).
- [ ] `regridding.py` (downscaling estatístico CMIP6 → grade local; validar contra INMET).
- [ ] `exposure.py` (overlay ativos × hazard via `ST_Intersects`/buffers → `fact_hazard_exposure`).
- [ ] Geometrias de Joinville/SC (malha IBGE) em `dim_region`.

## D6 — Modelagem física *(F1)*
**Pronto:** contrato `ScoreBand` + `compose_score` ([`scoring.py`](../../src/climate_esg/modeling/scoring.py)), testados.

**Falta:**
- [ ] `climate_indices.py`: índices xclim (Rx5day, R99pTOT, TX90p, WSDI, dias > 32°C) → `fact_climate_indicator`.
- [ ] `physical_risk.py`: hoje `NotImplementedError`. Implementar soma ponderada de indicadores normalizados por hazard (enchente, deslizamento, vento, calor) → `fact_physical_risk_score` com banda.
- [ ] Tabela de pesos por hazard externalizada em config (não em código) — ADR-0005/risco regulatório.
- [ ] Validação: coerência de sinal (enchente 2017 Joinville ↑ score).

## D7 — Modelagem de transição *(F2)*
**Pronto:** contrato definido; `transition_risk.py` é stub com semântica correta (soma ponderada, não XGBoost — ADR-0004).

**Falta:**
- [ ] `transition_risk.py`: soma ponderada calibrada de sub-scores (política/tecnológico/mercado) com banda → `fact_transition_risk_score`. `model_name='weighted_sum'`, `run_sk` registrado.
- [ ] Tabela de pesos calibrados a partir de NGFS/TCFD.
- [ ] Composição físico+transição via `compose_score` → score composto com banda.
- [ ] **(F3)** XGBoost só quando N≥30 (ADR-0004).

## D8 — Impacto financeiro *(F2/F3)*
**Falta (tudo):**
- [ ] `financial_impact.py`: DCF ajustado por fatores de cenário NGFS (provável via R — ver D14).
- [ ] **(F3)** VaR climático com Monte Carlo.

## D9 — Ingestão financeira/ESG/notícias *(F2)*
**Falta (tudo):**
- [ ] `filings_parser.py` (relatórios anuais, CDP, **formulários CVM** para Schulz; relatórios voluntários/GHG Protocol para Döhler — capital fechado).
- [ ] `market_data.py` (B3 SHUL3/SHUL4, Yahoo; Refinitiv só na Beta).
- [ ] `news_collector.py` (GDELT/RSS) — sinal ESG.
- [ ] Resolução de identidade LEI/CNPJ (GLEIF/OpenCorporates) para `dim_company`.

## D10 — NLP *(F2/F3)*
**Falta (tudo):**
- [ ] `extractors.py`: SLM (Phi-3 mini / Llama-3.2-3B) com **saída JSON validada** — escopo 1/2/3, metas, ano-alvo (F1>0.85).
- [ ] `classifiers.py`: ClimateBERT pt-BR + FinBERT (F2/F3).
- [ ] `rag.py` + pgvector + embeddings (bge-m3/e5-large): **Beta** (🔵).

## D11 — Governança, auditoria, MLOps *(F1+)*
**Pronto:** `dim_model_run`/`run_sk` no schema; diretório `governance/` vazio.

**Falta:**
- [ ] `lineage.py`: helper para criar `run_sk` (commit + hash do dado + params) antes de gravar qualquer fato.
- [ ] Integração **MLflow** (tracking URI já no config) nos flows.
- [ ] **Great Expectations / Pandera** nas transições bronze→prata→ouro (faixas físicas, NaN, LEI/CNPJ, saltos de score > 30pts).
- [ ] `model_cards.py` e `audit.py` (F2+).

## D12 — API FastAPI v1 *(F1/F2)*
**Pronto:** app FastAPI com `/health` e `/version`.

**Falta:**
- [ ] `routes/` + `schemas/` (Pydantic) + `deps.py` (sessão DB, auth).
- [ ] Endpoints MVP: `GET /v1/companies`, `/v1/companies/{lei}/scores`, `/v1/companies/{lei}/explanations/{run_sk}`, `/v1/regions/{id}/scores`, `/v1/assets/{id}/hazards`, `POST /v1/portfolios`.
- [ ] OAuth2 por persona (acionista/analista/auditor) — versão simples no MVP, RBAC completo no GA.

## D13 — Dashboard React *(F1/F2)*
**Falta (tudo):** `src/frontend/` vazio.
- [ ] Scaffold Vite + React + TS + Tailwind.
- [ ] Heatmap de carteira; drill-down por empresa (score + banda + sub-scores); mapa de ativos com hazards (Deck.gl).
- [ ] Cliente da API; gráficos (Recharts).

## D14 — R analytics *(F2/F3)*
**Falta (tudo):** `src/r_analytics/` vazio.
- [ ] `DESCRIPTION` + `renv.lock`.
- [ ] `ngfs_pathways.R`, `econometrics.R`, `validation.R` (backtest/calibração), `time_series.R`.
- [ ] Troca com Python via Parquet na camada ouro.

## D15 — Capacidades Beta/GA *(F3/F4 — 🔵 fora do MVP)*
- 🔵 RAG sobre relatórios; score regional; expansão setorial; piloto com investidor.
- 🔵 Agente conversacional; SSO/RBAC; observabilidade; IaC (Terraform/Helm); Docker/K8s; Redis cache.

---

## Caminho crítico para finalizar o MVP (16 semanas)

```
F0 (D1+D2+D3 E2E) ──► F1 (D3 v2 + D4 + D5 + D6 + D11 GE/MLflow + D12 scores + D13 mapa)
                                                   │
                                                   ▼
                                    F2 (D9 + D7 + D8 + D12 explain + D13 drill-down + D14)
                                                   │
                                                   ▼
                                          MVP entregue (físico + transição + dashboard)
```

**Desbloqueio imediato (ordem obrigatória):** D1 (ambiente+banco+Alembic+seed) → D2 (CI) → D3 (validate/promote + 1 NetCDF) → **smoke test E2E = F0 fechada**. Detalhamento por sprint em [`backlog-sprints.md`](backlog-sprints.md).
