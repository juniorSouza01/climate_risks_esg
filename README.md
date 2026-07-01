# Plataforma de Análise de Riscos Climáticos para ESG

> **Proprietary — All Rights Reserved.**
> © 2026 Osney Andrade de Souza Junior. Não distribuir, reproduzir ou criar obras derivadas sem autorização escrita do autor.

Plataforma que, a partir da **busca por uma empresa brasileira** (CNPJ, ticker ou nome), coleta dados de **múltiplas fontes públicas**, faz o **cruzamento** dessas informações e produz uma análise de **risco climático físico e de transição** alinhada a TCFD, ISSB IFRS S2 e cenários NGFS/IPCC — para suporte à decisão de investimento ESG.

**Princípio inegociável:** nenhum dado de empresa é fixo/hard-coded. Tudo é obtido automaticamente de fontes confiáveis, com **linhagem auditável** (cada fato carrega `run_sk` → commit + parâmetros + versão do dado). Scores são sempre entregues como **banda de incerteza**, nunca ponto único.

Documentação técnica de origem: [`docs/source/project.md`](docs/source/project.md). Decisões de arquitetura: [`docs/adrs/`](docs/adrs/) e [`docs/planning/`](docs/planning/).

---

## O que faz

Ao buscar uma empresa, o sistema monta um **dossiê consolidado**:

| Eixo | Fonte | Como |
|---|---|---|
| Cadastro (razão social, CNAE, sócios, situação, município) | **BrasilAPI** (CNPJ) | direto por CNPJ, ou via CNPJ resolvido da CVM |
| Mercado (preço, market cap, P/L, volatilidade) | **B3 / brapi.dev** | por ticker (requer `BRAPI_TOKEN`) |
| Financeiro (receita, lucro líquido) | **CVM Dados Abertos** (DFP) | casado por nome |
| Localização → código IBGE | **API de localidades do IBGE** | município/UF → código (automático) |
| **Risco climático municipal** (enchente, deslizamento) | **AdaptaBrasil (MCTI)** | por código IBGE, cenário SSP × horizonte |
| Notícias / controvérsia ESG | **GDELT** | por nome |
| Projeção climática (físico) | **CMIP6 / ESGF** | pipeline bronze→prata→ouro (Zarr) |

Sobre esse dado a plataforma roda **modelos** (scores físico/transição/composto com banda) e **ML** (similaridade de pares e detecção de anomalia via scikit-learn), tudo auditável. A geração de narrativa usa template determinístico — **o modelo calcula, o texto apenas comunica** (LLM nunca produz número).

> **Escopo:** foco no **Brasil** (BrasilAPI, CVM, B3, IBGE, AdaptaBrasil são nacionais). Empresas piloto internas: **Döhler** e **Schulz** (Joinville/SC).

---

## Arquitetura

Monólito modular Python sobre **PostgreSQL 16 + PostGIS + pgvector** (banco único), empacotado em **docker-compose**.

```
ingestão (esgf/CMIP6, b3/brapi, cvm, adaptabrasil, ibge, brasilapi, gdelt)
   → bronze/prata/ouro → star schema (dim_* / fact_* com run_sk)
   → modelagem (scoring, físico, transição, financeiro, peers, anomalia)
   → API FastAPI (/v1) → frontend React + TypeScript
```

- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2 + Alembic, scikit-learn, xarray/xclim, Prefect 3 (flows).
- **Frontend:** React + TypeScript + Vite (dashboard + busca de empresa), servido via nginx (proxy `/v1` → API).
- **Banco:** Postgres 16 + PostGIS + pgvector.

---

## Como executar

### Via Docker Compose (recomendado — sobe tudo)

Requisitos: Docker + Docker Compose.

```bash
# (opcional) token grátis da brapi.dev para dados de mercado da B3
export BRAPI_TOKEN=seu_token

docker compose up --build      # ou: make up
```

Sobe três serviços:

| Serviço | URL | Descrição |
|---|---|---|
| `frontend` | http://localhost:5173 | Dashboard + busca de empresa |
| `api` | http://localhost:8001 · `/docs` | FastAPI (aplica migrations + seed no startup) |
| `db` | localhost:5433 | Postgres 16 + PostGIS + pgvector |

Derrubar: `make down` (mantém o volume do banco).

### Ingerir dados (uma vez, com a stack no ar)

```bash
uv run climate-esg ingest b3-universe --target 200      # universo de empresas da B3
uv run climate-esg ingest cvm-financials --year 2023    # receita/lucro (DFP CVM)
uv run climate-esg geo resolve-ibge                      # código IBGE dos ativos (API IBGE)
uv run climate-esg ingest adaptabrasil                   # risco municipal (AdaptaBrasil)
make scores                                              # scores físico/transição/composto/financeiro
```

### Desenvolvimento local (sem Docker)

Requisitos: [`uv`](https://docs.astral.sh/uv/), PostgreSQL 16 + PostGIS + pgvector.

```bash
make install-dev          # cria venv + deps
make db-init              # role/db + extensões (precisa de sudo)
make db-migrate           # aplica o schema (Alembic)
make db-seed              # dimensões-base
make api                  # API em :8001 (API_PORT configurável)
cd src/frontend && npm install && npm run dev   # frontend em :5173
make check                # ruff + mypy + pytest
```

---

## Credenciais e tokens

Todas são **opcionais** — a plataforma sobe e busca empresas **sem nenhuma chave** (BrasilAPI, IBGE, AdaptaBrasil, CVM e GDELT são públicas e sem login). Configure só o que quiser destravar. Copie `.env.example` para `.env` e preencha, ou exporte no ambiente antes do `docker compose up`.

| Token | Para quê | Precisa? | Como obter |
|---|---|---|---|
| `BRAPI_TOKEN` | Mercado da B3 (preço, market cap, P/L) via **brapi.dev** | Recomendado | Conta grátis em **https://brapi.dev** → entrar (Google/GitHub/e-mail) → copiar o **token** no painel. Sem ele o bloco de mercado vem vazio/limitado. A **volatilidade anual** exige plano pago da brapi (o histórico de preços é bloqueado no plano grátis). |
| `PORTAL_TRANSPARENCIA_TOKEN` | **Contratos públicos** (clientes factuais + valores) via Portal da Transparência | Opcional (cadeia de valor) | Grátis com login **gov.br**: acesse **https://portaldatransparencia.gov.br/api-de-dados** → **"Cadastrar e-mail"** → você recebe a chave (`chave-api-dados`). Sem ele, a cadeia de valor mostra só fornecedor-gov (sem login) + sócios (QSA) + cadeia por CNAE. |
| `ESGF_OPENID` / `ESGF_PASSWORD` | Baixar CMIP6/ESGF quando um nó exigir login | Raramente | A maioria do CMIP6 é **aberta** (o download da F0 funcionou sem credencial). Se precisar, registre uma conta **OpenID** num nó ESGF (ex.: https://esgf-node.llnl.gov, CEDA, DKRZ) e use a URL OpenID + senha. Deixe vazio caso não precise. |

Exemplo de `.env`:

```bash
BRAPI_TOKEN=seu_token_brapi
PORTAL_TRANSPARENCIA_TOKEN=sua_chave_gov
# ESGF_OPENID= / ESGF_PASSWORD=  → deixe vazio (CMIP6 aberto)
```

No Docker, basta ter as variáveis no ambiente (ou no `.env`) antes de `docker compose up` — elas são repassadas ao serviço `api`.

---

## API (`/v1`)

| Endpoint | Descrição |
|---|---|
| `GET /v1/search?q=` | **Dossiê consolidado** de uma empresa (CNPJ/ticker/nome): cadastro + mercado + financeiro + clima + notícias |
| `GET /v1/companies` | Lista empresas (paginada) |
| `GET /v1/companies/{id}/scores` | Scores físico/transição/composto (banda) por cenário/horizonte |
| `GET /v1/companies/{id}/peers` | Pares por similaridade (ML) |
| `GET /v1/companies/{id}/anomaly` | Detecção de anomalia (ML) |
| `GET /v1/companies/{id}/financial` | Impacto financeiro projetado (DCF/NGFS) |
| `GET /v1/companies/{id}/explanations` | Narrativa explicativa do score |
| `GET /v1/assets/{id}/hazards` | Exposição a hazards por cenário/horizonte |
| `GET /v1/portfolio?scenario=&horizon=` | Agregado da carteira |
| `GET /v1/runs` · `GET /v1/model-cards/{run_sk}` | Linhagem / model cards (auditoria) |

---

## Estrutura

```
src/climate_esg/
  ingestion/   esgf_client, netcdf_loader, cf_validation, b3_universe,
               cvm, adaptabrasil, ibge, geocoding, market_data, news_collector, http
  geospatial/  regions, exposure
  modeling/    scoring, physical_risk, transition_risk, financial_impact,
               explanation, features, peers, anomaly, climate_indices
  governance/  lineage (run_sk + MLflow), model_cards, audit
  quality/     checks (Pandera + gates de faixa/salto)
  search/      dossier (busca multi-fonte + cruzamento)
  api/         FastAPI (routes, schemas, services, deps)
  db/          models (star schema), migrations (Alembic), seed
pipelines/flows/  ingest_cmip6, compute_scores (Prefect 3)
src/frontend/     React + TypeScript + Vite
infra/docker/     Dockerfiles (postgres+pgvector, api, frontend) + nginx
docs/             source (project.md), adrs, planning, architecture
```

---

## Princípios não negociáveis

1. **Dado de empresa nunca hard-coded** — sempre de fonte confiável, automaticamente.
2. **Modelos calculam, LLM apenas comunica.** Nenhum score numérico vem de LLM.
3. **Tudo auditável** — cada fato carrega `run_sk` (commit + dado + parâmetros).
4. **Banda de incerteza explícita** — score é faixa, nunca ponto.
5. **Comece simples** — soma ponderada → sklearn → modelos complexos só com ganho mensurável.

---

## Licença

Proprietária. Ver topo deste arquivo.
