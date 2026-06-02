# Backlog por Sprint — Execução do MVP (Azure Boards)

> Quebra de execução em **Épico → Feature → User Story → Task**, organizada em **8 sprints de 2 semanas** (16 semanas = MVP, conforme [`project.md`](../source/project.md) §11).
> Reconciliado com [ADRs](../adrs/) e [`entregaveis-e-gaps.md`](entregaveis-e-gaps.md).
> Para importar no Azure DevOps Boards, use [`azure-boards-import.csv`](azure-boards-import.csv) (ver instruções no fim).

**Mapa de sprints ↔ fases:**

| Sprint | Semanas | Fase | Foco |
|---|---|---|---|
| S1 | 1–2 | F0 | Ambiente + banco + Alembic + seed + CI |
| S2 | 3–4 | F0→F1 | Pipeline E2E (validate/promote) + smoke test + governança base |
| S3 | 5–6 | F1 | Requisição ESGF v2 + ingestão lote + geoespacial base |
| S4 | 7–8 | F1 | Exposição + índices xclim → fatos climáticas |
| S5 | 9–10 | F1 | Score físico + API scores + dashboard (scaffold + mapa) |
| S6 | 11–12 | F2 | Ingestão financeira/ESG + identidade + NLP extractors |
| S7 | 13–14 | F2 | Score transição + composto + impacto financeiro (R) + API explain |
| S8 | 15–16 | F2 | Dashboard drill-down + validação R + hardening + fecho MVP |

> Convenção de `Iteration Path` no Azure: `Climate ESG\Sprint 1` … `Climate ESG\Sprint 8`.

---

## ÉPICO 1 — Fundação, Ambiente & Banco *(F0)*

### Feature 1.1 — Provisionar ambiente local
- **US 1.1.1** — Como dev, quero o ambiente Python provisionado para rodar o código. *(S1)*
  - [ ] Instalar `uv`; criar `.venv`; `uv sync --extra dev`; commitar `uv.lock`.
  - [ ] Validar `make check` (ruff + mypy + pytest) verde localmente.
  - [ ] Criar `.env` a partir de `.env.example`.
- **US 1.1.2** — Como dev, quero o Postgres inicializado com extensões. *(S1)*
  - [ ] Rodar `infra/local/setup_postgres.sh` (apt: postgres-16, postgis, pgvector).
  - [ ] Rodar `infra/local/init_db.sh` (role `climate_esg`, db, extensões postgis/vector/pg_trgm).
  - [ ] Smoke: `make db-shell` conecta e `\dx` lista extensões.

### Feature 1.2 — Migrations Alembic
- **US 1.2.1** — Como dev, quero materializar o star schema via migrations versionadas. *(S1)*
  - [ ] Criar `alembic.ini` + `src/climate_esg/db/migrations/env.py` apontando para `Base.metadata`.
  - [ ] Gerar migration inicial (autogenerate) com todas as dimensões + 3 fatos atuais.
  - [ ] Adicionar índices GIST em `dim_asset.geom`/`dim_region.geom`.
  - [ ] `make db-migrate` aplica sem erro; validar tabelas no banco.

### Feature 1.3 — Seed de dimensões
- **US 1.3.1** — Como modelador, quero as dimensões-base populadas para o pipeline ter chaves. *(S1)*
  - [ ] `db/seed.py`: `dim_scenario` (historical, SSP2-4.5, SSP5-8.5).
  - [ ] `dim_climate_variable` (CF: tasmin, tasmax, pr, sfcWindmax, hurs, huss…).
  - [ ] `dim_company`: Döhler (capital fechado) e Schulz (B3 SHUL3/SHUL4).
  - [ ] `dim_asset`: plantas em Joinville/SC com lat/long (PostGIS POINT).
  - [ ] `dim_date`: calendário 1988–2050 (BR fiscal-aware).
  - [ ] Comando CLI `climate-esg db seed` idempotente.

---

## ÉPICO 2 — CI/CD & Qualidade *(F0)*

### Feature 2.1 — CI no GitHub Actions
- **US 2.1.1** — Como dev, quero CI verde a cada push. *(S1)*
  - [ ] `.github/workflows/ci.yml`: ruff + mypy + pytest.
  - [ ] **Postgres como service container** para testes `integration`.
  - [ ] Gate de cobertura mínima.
- **US 2.1.2** — Como dev, quero hooks de pré-commit. *(S1)*
  - [ ] `.pre-commit-config.yaml` (ruff format/check, mypy leve, fim de arquivo).

---

## ÉPICO 3 — Ingestão & Pipeline CMIP6 E2E *(F0→F1)*

### Feature 3.1 — Completar o flow `ingest_cmip6`
- **US 3.1.1** — Como pipeline, quero validar o NetCDF baixado. *(S2)*
  - [ ] Implementar `validate_netcdf`: abrir com xarray + cf-xarray; checar variável/unidade/dims; ranges físicos.
  - [ ] Teste `needs_data` com 1 arquivo `tasmin`.
- **US 3.1.2** — Como pipeline, quero promover bronze→prata em Zarr. *(S2)*
  - [ ] Implementar `promote_to_silver`: regrid grade comum + recorte SC/Brasil + escrita Zarr (Zstd).
  - [ ] Catálogo `intake-esm` da prata.
- **US 3.1.3** — Como dev, quero o smoke test E2E que fecha a F0. *(S2)*
  - [ ] Baixar 1 NetCDF `tasmin` historical para `data/bronze`.
  - [ ] Flow `ingest_cmip6` com `do_validate=True, do_promote=True` → Zarr na prata.
  - [ ] Materializar ≥1 indicador em `fact_climate_indicator` com `run_sk`. **(Critério de saída F0)**

### Feature 3.2 — Expansão de variáveis (v2) *(F1 — ADR-0005)*
- **US 3.2.1** — Como modelador, quero as variáveis de hazard de SC. *(S3)*
  - [ ] Gerar requisição MetaGrid ESGF: `pr`, `tasmax`, `sfcWindmax` × `historical+ssp245+ssp585` × EC-Earth3.
  - [ ] Arquivar scripts `v2_*` em `data/manifests/cmip6_wget/`.
- **US 3.2.2** — Como pipeline, quero ingerir a v2 em lote. *(S3)*
  - [ ] Deployment/schedule Prefect (`prefect.yaml`) para ingestão em lote.
  - [ ] Rodar fetch+validate+promote para todas as variáveis v2.

---

## ÉPICO 4 — Geoespacial & Exposição *(F1)*

### Feature 4.1 — Operações raster e regridding
- **US 4.1.1** — Como modelador, quero operações raster reutilizáveis. *(S3)*
  - [ ] `geospatial/raster_ops.py` (reamostragem, recorte, CRS via rioxarray/rasterio).
  - [ ] `geospatial/regridding.py` (downscaling CMIP6 → grade local; validar vs INMET/ERA5).
### Feature 4.2 — Exposição ativo × hazard
- **US 4.2.1** — Como analista, quero a exposição por planta. *(S4)*
  - [ ] Carregar malha IBGE de Joinville/SC em `dim_region`.
  - [ ] `geospatial/exposure.py`: overlay raster hazard × `dim_asset` (`ST_Intersects`/buffer).
  - [ ] Modelar e popular `fact_hazard_exposure` (migration nova).

---

## ÉPICO 5 — Modelagem de Risco Físico *(F1)*

### Feature 5.1 — Índices climáticos (xclim)
- **US 5.1.1** — Como modelador, quero índices climáticos por ativo. *(S4)*
  - [ ] `modeling/climate_indices.py`: Rx5day, R99pTOT, TX90p, WSDI, dias > 32°C.
  - [ ] Materializar em `fact_climate_indicator` (asset × var × cenário × tempo).
  - [ ] Validação xclim: erro < 1% vs indicadores publicados.

### Feature 5.2 — Score físico
- **US 5.2.1** — Como analista, quero o score físico com banda. *(S5)*
  - [ ] Tabela de **pesos por hazard** em config (enchente/deslizamento/vento/calor).
  - [ ] Implementar `modeling/physical_risk.py`: soma ponderada normalizada → `ScoreBand`.
  - [ ] Persistir `fact_physical_risk_score` (company × cenário × horizonte × `run_sk`).
  - [ ] Validar coerência: enchente 2017 Joinville ↑ score das duas empresas.

---

## ÉPICO 6 — Ingestão Financeira/ESG & NLP *(F2)*

### Feature 6.1 — Coletores financeiros/ESG
- **US 6.1.1** — Como pipeline, quero coletar dados públicos das empresas. *(S6)*
  - [ ] `ingestion/filings_parser.py`: CVM (Schulz), relatórios voluntários/GHG/CDP (Döhler).
  - [ ] `ingestion/market_data.py`: B3 SHUL3/SHUL4, Yahoo.
  - [ ] Resolução de identidade LEI/CNPJ (GLEIF/OpenCorporates) → `dim_company`.
- **US 6.1.2** — Como pipeline, quero sinal de notícias ESG. *(S6, opcional MVP)*
  - [ ] `ingestion/news_collector.py` (GDELT/RSS) → `fact_news_signal`.

### Feature 6.2 — Extração NLP com saída validada
- **US 6.2.1** — Como modelador, quero extrair metas/emissões de relatórios. *(S6)*
  - [ ] `nlp/extractors.py`: SLM (Phi-3 mini/Llama-3.2-3B) → **JSON validado** (escopo 1/2/3, ano-alvo, % redução).
  - [ ] Meta de aceitação F1 > 0.85 nos campos críticos.

---

## ÉPICO 7 — Modelagem de Transição & Score Composto *(F2)*

### Feature 7.1 — Score de transição (soma ponderada — ADR-0004)
- **US 7.1.1** — Como analista, quero o score de transição com banda. *(S7)*
  - [ ] Tabela de **pesos calibrados** (NGFS/TCFD) em config.
  - [ ] Implementar `modeling/transition_risk.py`: soma ponderada de sub-scores (política/tecnológico/mercado).
  - [ ] Persistir `fact_transition_risk_score` (`model_name='weighted_sum'`, `run_sk`).

### Feature 7.2 — Score composto + impacto financeiro
- **US 7.2.1** — Como analista, quero o score composto físico+transição. *(S7)*
  - [ ] Compor via `compose_score` → banda combinada.
- **US 7.2.2** — Como analista, quero a projeção de impacto financeiro. *(S7)*
  - [ ] `modeling/financial_impact.py` ou R: DCF ajustado por fatores NGFS.

---

## ÉPICO 8 — API FastAPI v1 *(F1/F2)*

### Feature 8.1 — Endpoints de leitura
- **US 8.1.1** — Como frontend, quero consultar empresas e scores. *(S5)*
  - [ ] `api/deps.py` (sessão DB), `api/schemas/` (Pydantic), `api/routes/`.
  - [ ] `GET /v1/companies`, `GET /v1/companies/{lei}/scores` (bandas + `run_sk`).
  - [ ] `GET /v1/assets/{id}/hazards`, `GET /v1/regions/{id}/scores`.
- **US 8.1.2** — Como auditor, quero a explicação de um score. *(S7)*
  - [ ] Modelar `fact_score_explanation`; `GET /v1/companies/{lei}/explanations/{run_sk}`.
- **US 8.1.3** — Como investidor, quero registrar carteira. *(S8)*
  - [ ] `POST /v1/portfolios` + agregados.
  - [ ] OAuth2 simples por persona (acionista/analista/auditor).

---

## ÉPICO 9 — Dashboard React *(F1/F2)*

### Feature 9.1 — Scaffold + mapa
- **US 9.1.1** — Como analista, quero ver o mapa de ativos e hazards. *(S5)*
  - [ ] Scaffold Vite + React + TS + Tailwind em `src/frontend`.
  - [ ] Cliente da API; mapa de ativos com hazards (Deck.gl).
### Feature 9.2 — Heatmap & drill-down
- **US 9.2.1** — Como investidor, quero o heatmap de carteira e o drill-down. *(S8)*
  - [ ] Heatmap de carteira; drill-down por empresa (score + banda + sub-scores; Recharts).

---

## ÉPICO 10 — Governança, Auditoria & MLOps *(transversal, F1+)*

### Feature 10.1 — Linhagem e tracking
- **US 10.1.1** — Como auditor, quero linhagem completa de cada score. *(S2)*
  - [ ] `governance/lineage.py`: cria `run_sk` (commit + hash do dado + params) antes de gravar fato.
  - [ ] Integrar **MLflow** nos flows (tracking URI já no config).
### Feature 10.2 — Qualidade de dado
- **US 10.2.1** — Como pipeline, quero bloquear dado ruim. *(S4)*
  - [ ] Great Expectations/Pandera em bronze→prata→ouro (faixas físicas, NaN, LEI/CNPJ, salto > 30pts).
### Feature 10.3 — Model cards *(S8)*
  - [ ] `governance/model_cards.py` a partir de metadados MLflow.

---

## ÉPICO 11 — Validação Independente em R *(F2/F3)*

### Feature 11.1 — Setup e cenários NGFS
- **US 11.1.1** — Como validador, quero ambiente R reprodutível. *(S7)*
  - [ ] `src/r_analytics/DESCRIPTION` + `renv.lock`.
  - [ ] `ngfs_pathways.R` (tratamento de cenários).
- **US 11.1.2** — Como validador, quero checar os scores Python. *(S8)*
  - [ ] `validation.R` (backtest/calibração); troca via Parquet na camada ouro.

---

## ÉPICO 12 — Fecho do MVP & Hardening *(F2)*

### Feature 12.1 — Critério de saída do MVP
- **US 12.1.1** — Como PO, quero o MVP demonstrável. *(S8)*
  - [ ] Score composto (físico + transição) com banda para Döhler e Schulz nos 3 cenários × 3 horizontes.
  - [ ] Dashboard navegável internamente (heatmap + drill-down + mapa).
  - [ ] Estabilidade trimestral < 5%; coerência de sinal validada.
  - [ ] Runbook de reprodução E2E + atualização dos ADRs.

---

## 🔵 Fora do MVP (Beta/GA — backlog futuro)
RAG sobre relatórios (pgvector + bge-m3); score regional; expansão setorial; XGBoost de transição (N≥30); agente conversacional; SSO/RBAC; observabilidade; IaC (Terraform/Helm); Docker/K8s; Redis; Refinitiv/MSCI.

---

## Como importar no Azure DevOps Boards

1. **Boards → Work Items → Import Work Items** → selecione [`azure-boards-import.csv`](azure-boards-import.csv).
2. O CSV traz `Work Item Type`, `Title`, `Description`, `Tags`, `Iteration Path`, `Priority`.
3. A hierarquia (Epic→Feature→Story) é importada **plana**; vincule com **Add link → Parent** ou agrupe pela coluna `Tags` (nome do épico). Alternativa: importar nível a nível (Épicos → Features → Stories) usando a coluna `Parent` com o ID gerado.
4. Crie antes os **Iteration Paths** `Sprint 1`…`Sprint 8` em **Project Settings → Boards → Project configuration → Iterations**.
5. As **Tasks** (checkboxes deste documento) podem ser adicionadas manualmente sob cada User Story ou expandidas no CSV se preferir granularidade total no board.
