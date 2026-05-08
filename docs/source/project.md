# Plataforma de Análise de Riscos Climáticos para ESG

**Documento Técnico de Arquitetura e Plano de Desenvolvimento**

Versão 2.0 — Documento expandido para início de desenvolvimento

Autor: Osney Andrade de Souza Junior
Data: 07 de maio de 2026

---

## 1. Introdução e contexto

Este documento dá sequência à proposta inicial da Plataforma de Análise de Riscos Climáticos para ESG, expandindo a arquitetura para um nível de detalhe suficiente para iniciar o desenvolvimento. O objetivo aqui não é repetir o documento conceitual, e sim consolidar decisões técnicas, definir separação de módulos, modelagem de dados, escolha de bancos, papel das linguagens (Python e R), pipeline de ingestão de dados climáticos do CMIP6 via ESGF, e o plano de implementação do MVP.

A motivação permanece a mesma: investidores institucionais e acionistas precisam de uma visão integrada e auditável de riscos climáticos físicos e de transição por empresa e por região, alinhada a TCFD, ISSB IFRS S2 e cenários NGFS/IPCC. O que muda nesta versão é que já temos massa de dados real do ESGF (CMIP6 EC-Earth3 histórico) baixada, o que permite ancorar o projeto em fontes concretas em vez de tratá-las como abstração.

As decisões registradas aqui devem ser tratadas como ponto de partida para o repositório. Algumas serão refinadas durante o desenvolvimento — explicitamos onde isso é esperado.

---

## 2. Escopo do MVP e princípios de design

### 2.1. Escopo do MVP (primeiras 16 semanas)

O MVP é deliberadamente estreito. Ampliar antes de validar é a falha mais comum nesse tipo de projeto.

- Cobertura inicial: 10 empresas piloto de um único setor (sugestão: agronegócio brasileiro listado em B3, alta exposição a hazard climático e dado público disponível).
- Dois cenários climáticos: SSP2-4.5 (intermediário) e SSP5-8.5 (alto), além do histórico para calibração.
- Dois pilares de risco no MVP: risco físico (com dados CMIP6 baixados) e risco de transição (modelo tabular básico). O pilar de capacidade de adaptação fica para a fase Beta.
- Três horizontes: 2030, 2040, 2050.
- Frontend mínimo: dashboard estático com heatmap de carteira, drill-down por empresa, mapa de ativos com hazards sobrepostos.
- Sem agente conversacional no MVP. RAG sobre relatórios anuais entra na Beta.

### 2.2. Princípios de design não negociáveis

- **Modelos especializados calculam, LLM apenas comunica e extrai.** Nenhum score numérico final é produzido por LLM. Ela apenas (a) extrai informação não estruturada, (b) gera narrativa de explicação, (c) atua como interface conversacional na fase Beta em diante.
- **Tudo é auditável.** Cada score tem linhagem de dado, versão de modelo, versão de código e parâmetros registrados. Sem isso, o produto não passa em uma due diligence séria.
- **Reprodutibilidade reforçada.** Todo experimento e todo score precisam ser reprodutíveis a partir de (dado versionado, código versionado, ambiente versionado). Caso contrário, não vai.
- **Bandas de incerteza explícitas.** Cenários climáticos têm incerteza estrutural alta. Score é entregue como faixa, nunca como ponto único.
- **Comece simples.** Soma ponderada calibrada antes de XGBoost. XGBoost antes de redes neurais. Foundation models climáticos só quando houver ganho mensurável sobre baseline.

---

## 3. Visão arquitetural detalhada

### 3.1. Camadas e fluxo de dados

A arquitetura permanece em cinco camadas, mas agora com responsabilidades bem delimitadas e tecnologias escolhidas. O fluxo é unidirecional: ingestão → armazenamento → modelagem → orquestração → apresentação. Não há atalhos.

| Camada | Função | Tecnologia escolhida |
|---|---|---|
| 1. Ingestão | Coleta de dados climáticos (ESGF/CMIP6), financeiros, ESG, regulatórios, geoespaciais e textuais | Apache Airflow (orquestração), wget/Globus para ESGF, requests/httpx para APIs, scrapy controlado, Kafka opcional na Beta |
| 2. Armazenamento | Lake bronze/prata/ouro, banco analítico relacional, banco geoespacial, banco vetorial, object store para raster | MinIO/S3 (data lake e raster), PostgreSQL 16 + PostGIS (relacional + geo), pgvector (embeddings), DuckDB (analítico local), Delta Lake / Iceberg sobre S3 |
| 3. Modelagem | Modelos climáticos, geoespaciais, tabulares, NLP/SLM, econométricos | Python 3.11 (xarray, dask, scikit-learn, XGBoost, PyTorch, transformers); R 4.4 (estatística, séries macro, validação) |
| 4. Orquestração de IA | Composição de modelos, geração de narrativa, RAG (Beta+) | LangChain/LlamaIndex, vLLM/Ollama local para SLM, API externa apenas para LLM grande |
| 5. Apresentação | Dashboard, API pública, exportação | FastAPI (backend), React + TypeScript + Mapbox/Deck.gl (frontend), pgREST opcional para read-only |

### 3.2. Diagrama lógico (descrição textual)

Em alto nível: dados externos chegam via Airflow nos buckets bronze. DAGs específicas validam, normalizam e promovem para prata, com chave canônica de empresa (LEI/CNPJ) e geometria validada em PostGIS. Camada ouro materializa features e fatos prontos para consumo (modelos e dashboard). Modelos lêem da camada ouro, escrevem scores e métricas em tabelas dedicadas com versionamento. API expõe agregações ao dashboard. LLMs e SLMs consultam tanto o banco vetorial (RAG) quanto a API analítica via tools.

Princípio importante: nenhum componente de modelagem grava direto na camada bronze ou prata. Todo writeback é feito em tabelas próprias (scores, explanations, runs), preservando a linhagem de dado de origem.

---

## 4. Separação de módulos e estrutura do repositório

O repositório é um monorepo, organizado por domínio funcional. Esta estrutura é a recomendação para iniciar; alguns módulos podem ser extraídos para repositórios independentes quando atingirem maturidade.

```
climate-esg-platform/
├── README.md
├── pyproject.toml                  # Dependências Python (uv ou poetry)
├── renv.lock                       # Dependências R (renv)
├── docker-compose.yml              # Stack local: Postgres+PostGIS, MinIO, Airflow
├── Makefile                        # Atalhos: make ingest, make train, make api
├── .github/
│   └── workflows/                  # CI: lint, testes, build de imagens
├── infra/
│   ├── terraform/                  # IaC para nuvem (fase Beta+)
│   ├── docker/                     # Dockerfiles por serviço
│   └── helm/                       # Charts Kubernetes (fase GA)
├── data/
│   ├── bronze/                     # (gitignored) Dados brutos locais
│   ├── silver/                     # (gitignored) Dados limpos locais
│   └── samples/                    # Pequenos exemplos versionados p/ testes
├── pipelines/                      # Airflow DAGs
│   ├── dags/
│   │   ├── ingest_cmip6.py
│   │   ├── ingest_esg_filings.py
│   │   ├── ingest_market_data.py
│   │   ├── ingest_news.py
│   │   └── compute_scores.py
│   └── plugins/                    # Operadores e hooks customizados
├── src/
│   ├── climate_esg/                # Pacote Python principal
│   │   ├── ingestion/
│   │   │   ├── esgf_client.py      # Cliente CMIP6/ESGF (parser dos wget)
│   │   │   ├── netcdf_loader.py    # Leitura xarray + Dask
│   │   │   ├── filings_parser.py   # Relatórios anuais, CDP, CVM
│   │   │   ├── market_data.py      # B3, Yahoo, Refinitiv (quando contratado)
│   │   │   └── news_collector.py   # GDELT, RSS, scrapers
│   │   ├── geospatial/
│   │   │   ├── raster_ops.py       # Reamostragem, recortes, CRS
│   │   │   ├── exposure.py         # Overlay ativos × hazards
│   │   │   └── regridding.py       # Downscaling estatístico
│   │   ├── modeling/
│   │   │   ├── physical_risk.py    # Indicadores físicos por ativo
│   │   │   ├── transition_risk.py  # XGBoost / LightGBM tabular
│   │   │   ├── climate_indices.py  # Heatwave, drought, SPEI, etc.
│   │   │   ├── financial_impact.py # DCF ajustado, VaR climático
│   │   │   └── scoring.py          # Composição final do score
│   │   ├── nlp/
│   │   │   ├── extractors.py       # SLM/LLM com saída JSON validada
│   │   │   ├── classifiers.py      # ClimateBERT, FinBERT
│   │   │   └── rag.py              # Indexação e recuperação (Beta+)
│   │   ├── governance/
│   │   │   ├── lineage.py          # Linhagem de dado e modelo
│   │   │   ├── model_cards.py      # Geração de model cards
│   │   │   └── audit.py            # Trilha de auditoria
│   │   ├── api/
│   │   │   ├── main.py             # FastAPI entrypoint
│   │   │   ├── routes/
│   │   │   ├── schemas/            # Pydantic
│   │   │   └── deps.py             # Injeção (DB, auth)
│   │   ├── db/
│   │   │   ├── models.py           # SQLAlchemy ORM
│   │   │   ├── migrations/         # Alembic
│   │   │   └── seed.py
│   │   └── utils/
│   ├── r_analytics/                # Código R
│   │   ├── DESCRIPTION
│   │   ├── R/
│   │   │   ├── time_series.R       # ARIMA, Prophet, fable
│   │   │   ├── econometrics.R      # VAR, cointegração
│   │   │   ├── validation.R        # Backtest, calibração
│   │   │   └── ngfs_pathways.R     # Tratamento de cenários NGFS
│   │   └── tests/
│   └── frontend/                   # React + TS
│       ├── package.json
│       ├── src/
│       │   ├── components/
│       │   ├── pages/
│       │   ├── api/
│       │   └── lib/
│       └── public/
├── notebooks/                      # Exploratórios. Não vão para produção.
├── tests/
│   ├── unit/
│   ├── integration/
│   └── data/                       # Fixtures e expectativas Great Expectations
└── docs/
    ├── architecture/
    ├── adrs/                       # Architecture Decision Records
    ├── data_dictionary.md
    └── runbooks/
```

### 4.1. Justificativa para monorepo

Em fase inicial, monorepo reduz fricção: uma única CI, uma única convenção de versionamento, e refactors atravessam módulos sem coordenação entre repositórios. Quando o frontend, a API e os pipelines tiverem cadências de release diferentes (esperado a partir da fase GA), considerar split — por enquanto, agrupar reduz custo cognitivo.

---

## 5. Papel de Python e R no projeto

A pergunta de qual linguagem usar é, na prática, uma decisão por subproblema. Python é a linguagem default para tudo que toca produção (pipelines, API, modelos em runtime, integrações). R entra onde tem vantagem clara: estatística aplicada, séries macroeconômicas, validação independente. Misturar as duas é normal em projetos de finanças sustentáveis.

### 5.1. Python — espinha dorsal

- Ingestão e ETL: Airflow, requests/httpx, polars/pandas, geopandas.
- Dados climáticos: xarray + Dask para manipular NetCDF do CMIP6 sem estourar memória; rioxarray para georeferenciamento; cf-xarray para metadados CF.
- Geoespacial: shapely, geopandas, rasterio, pyproj.
- Machine learning tabular: scikit-learn, XGBoost, LightGBM, CatBoost; SHAP para interpretabilidade.
- Deep learning (quando justificado): PyTorch, com Lightning; transformers (HuggingFace) para SLM/LLM.
- API: FastAPI + Pydantic v2 + SQLAlchemy 2.x + Alembic.
- Validação de dado: Great Expectations ou Pandera nas transições bronze→prata→ouro.
- Tracking de experimentos: MLflow.

### 5.2. R — análise estatística e validação

R não é nostalgia. Em finanças sustentáveis, a literatura econométrica está em R, e várias bibliotecas de séries temporais (forecast, fable, tsibble) e de finanças quantitativas (PerformanceAnalytics, quantmod, rugarch) ainda têm vantagem prática sobre equivalentes Python.

- Modelagem econométrica de cenários NGFS: VAR, cointegração, modelos de fator com pacote `vars` e `tsibble`.
- Backtesting de scores compostos contra retornos ajustados a risco: `PerformanceAnalytics`.
- Validação independente de modelos Python: relatórios de calibração e robustez gerados em Quarto/RMarkdown como segunda fonte de avaliação, reduzindo confirmation bias.
- Modelos bayesianos hierárquicos para incerteza em score regional: `brms` / `rstan`.

### 5.3. Interoperabilidade

Python e R conversam por três caminhos:

- Arquivos Parquet trocados via camada ouro do data lake. Padrão para volumes maiores.
- Arrow / DuckDB para zero-copy quando ambos rodam na mesma máquina.
- `reticulate` (R chamando Python) ou `rpy2` (Python chamando R) apenas em casos pontuais; preferir troca por Parquet.

---

## 6. Modelagem de dados

### 6.1. Camadas do data lake

| Camada | Conteúdo | Formato | Particionamento |
|---|---|---|---|
| Bronze | Dados brutos como recebidos. NetCDF do CMIP6 inalterados, PDFs de relatórios, JSONs de APIs. | Original (NetCDF, PDF, JSON, CSV) | Por fonte e data de ingestão |
| Prata | Dados limpos, padronizados, com chaves canônicas. Climático regrided para grade comum, empresas com LEI/CNPJ resolvido. | Parquet (tabular), Zarr (raster) | Por entidade (empresa, região, variável climática) e ano |
| Ouro | Features e fatos modelados, prontos para consumo de modelo e dashboard. | Parquet + tabelas Postgres materializadas | Por modelo de consumo (star schema) |

### 6.2. Modelagem dimensional na camada ouro (star schema)

Para análise e dashboard, a camada ouro é organizada em star schema. Há dois grandes modelos estrela, um para risco físico e outro para risco de transição, compartilhando dimensões de empresa, região, tempo e cenário. Essa separação evita explosão dimensional ao mesmo tempo que mantém consultas analíticas eficientes.

#### 6.2.1. Dimensões compartilhadas

| Dimensão | Chave | Atributos principais |
|---|---|---|
| `dim_company` | `company_sk` (surrogate) | lei, cnpj, ticker, nome, setor_nace, subsetor, país_sede, controlador, data_ipo, market_cap_band, scd_type_2 (validity_from/to) |
| `dim_asset` | `asset_sk` | company_sk, tipo (planta, fazenda, escritório), latitude, longitude, geom (PostGIS), capacidade, capex_aprox, data_inauguração, status |
| `dim_region` | `region_sk` | iso_country, admin1, admin2, geom, hierarchy_path, população, pib |
| `dim_date` | `date_sk` | date, ano, trimestre, mês, dia_da_semana, é_fim_de_ano_fiscal_BR |
| `dim_scenario` | `scenario_sk` | framework (NGFS/IPCC), nome (SSP2-4.5, NetZero2050…), horizonte, descrição, fonte, versão |
| `dim_climate_variable` | `var_sk` | código_CF (tas, tasmin, pr, hus…), unidade, descrição, fonte (CMIP6 model+experiment+member) |
| `dim_model_run` | `run_sk` | model_name, model_version, code_commit, train_data_version, train_date, hiperparâmetros_json |

#### 6.2.2. Tabelas fato

| Fato | Grão | Métricas principais |
|---|---|---|
| `fact_climate_indicator` | asset_sk × var_sk × scenario_sk × date_sk (mensal) | valor_médio, valor_max, valor_min, anomalia_vs_baseline, percentil |
| `fact_hazard_exposure` | asset_sk × hazard_type × scenario_sk × horizon | exposição_normalizada (0-1), retorno_de_período, fração_capex_em_risco |
| `fact_physical_risk_score` | company_sk × scenario_sk × horizon × run_sk | score_0_100, banda_baixa, banda_alta, n_ativos, cobertura_% |
| `fact_transition_risk_score` | company_sk × scenario_sk × horizon × run_sk | score_0_100, intensidade_carbono, alinhamento_metas, sub_score_política, sub_score_tecnológico |
| `fact_score_explanation` | company_sk × run_sk | shap_values_json, narrativa_md, fontes_citadas (array de doc_ids) |
| `fact_news_signal` | company_sk × date_sk | sentimento_esg, controvérsia_score, contagem_artigos, top_topics_json |

#### 6.2.3. Notas de design

- Surrogate keys (`sk`) são integer auto-incrementadas, não as chaves naturais. Isso permite SCD Tipo 2 limpo em `dim_company` quando uma empresa muda de controle ou setor.
- Score nunca é armazenado sem `run_sk`. Recalcular o mesmo score por mudança metodológica gera nova linha, não update.
- `fact_climate_indicator` pode ficar enorme (ativo × variável × cenário × tempo). Particionar por `scenario_sk` e ano. Considerar arquivar em Parquet/Iceberg e materializar agregações para Postgres.
- `dim_region` implementada como PostGIS com índice GIST sobre `geom`; consultas de exposição usam `ST_Intersects`.

### 6.3. Dados raster e o problema NetCDF

O CMIP6 chega em NetCDF (extensão `.nc`). Os arquivos baixados via ESGF cobrem variáveis como `tasmin` (temperatura mínima do ar), `hurs`/`huss` (umidade), `prsn` (neve), `rsdt` (radiação solar no topo da atmosfera), `uo` (corrente oceânica) e `sivol` (volume de gelo marinho), entre outras, do modelo EC-Earth3 com membros r120/r121/r132 do experimento histórico. Cada arquivo é um ano (ex.: `rsdt_Amon_EC-Earth3_historical_r120i1p1f1_gr_198801-198812.nc`).

Tratamento prático:

- Manter os NetCDF originais em S3/MinIO bronze, organizados por `dataset_id` (ex.: `CMIP6.CMIP.EC-Earth-Consortium.EC-Earth3.historical.r120i1p1f1.Amon.tasmin.gr.v20200412`).
- Promoção para prata em Zarr, regridded para grade comum (ex.: 1° × 1° ou grade nativa preservada se for o caso de uso). Zarr é amigável a Dask e a I/O por chunk.
- Catálogo via `intake-esm`: gera manifestos pesquisáveis a partir dos diretórios CMIP6, evita carregar metadado a cada DAG.
- Cálculo de indicadores climáticos (heatwaves, dias acima de threshold, SPEI) feito em Python com `xclim`. Resultados materializados em `fact_climate_indicator`.

### 6.4. Embeddings e banco vetorial (pgvector)

RAG e busca semântica de documentos usam pgvector como extensão do mesmo Postgres. Vantagem: uma única instância, joins entre tabela vetorial e dimensões relacionais, transações ACID.

```sql
-- Tabela de chunks de documentos com embedding
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE doc_chunks (
    chunk_id      BIGSERIAL PRIMARY KEY,
    document_id   BIGINT NOT NULL REFERENCES documents(document_id),
    company_sk    INT REFERENCES dim_company(company_sk),
    chunk_index   INT NOT NULL,
    text          TEXT NOT NULL,
    embedding     vector(1024),         -- bge-m3 ou e5-large-v2
    page_number   INT,
    section       TEXT,
    inserted_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON doc_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX ON doc_chunks (company_sk);
```

Modelo de embedding inicial: `bge-m3` ou `e5-large-v2` (multilíngues, free, suportam pt-BR). Avaliar custo/benefício de OpenAI/Voyage embeddings na Beta — em geral, modelos open superam para domínio específico após fine-tuning leve.

### 6.5. Por que Postgres + pgvector e não dois bancos?

Outras escolhas razoáveis seriam Weaviate, Qdrant ou Pinecone para vetores, e Postgres apenas para transacional. A escolha por pgvector se justifica por:

- Operação simplificada: uma única instância para administrar, backup, replicar e auditar.
- Joins relacionais com filtros transacionais (ex.: "busca semântica entre relatórios da empresa X publicados após 2023") saem em uma query, sem orquestração entre dois sistemas.
- Performance de pgvector com índice HNSW é suficiente para o volume previsto (milhões de chunks, não bilhões). Se atingirmos esse limite, a migração para um banco vetorial dedicado é viável e isolada na camada `nlp/rag.py`.

Conclusão: começar com Postgres único (PostGIS + pgvector). Reavaliar quando o volume de chunks ultrapassar ~50 milhões ou a latência p95 piorar.

### 6.6. Outros bancos considerados

| Banco | Papel | Decisão |
|---|---|---|
| PostgreSQL + PostGIS + pgvector | OLTP, geoespacial, vetorial, dimensões e fatos compactos | Adotado como banco principal |
| DuckDB | Análise local em Parquet, notebooks, EDA, runs de modelo offline | Adotado como ferramenta de análise (não como banco persistente) |
| MinIO/S3 | Object store para bronze, prata raster (Zarr), modelos e artefatos MLflow | Adotado |
| ClickHouse | Analítico colunar de altíssimo volume (séries de hazards horárias) | Não adotado no MVP. Considerar na Beta se `fact_climate_indicator` passar de ~1B linhas |
| Neo4j | Grafo de relacionamentos (controlador, cadeia, contraparte) | Não adotado no MVP. Reavaliar quando o pilar de risco de cadeia entrar |
| Redis | Cache de respostas da API e fila leve | Adotado como infraestrutura auxiliar a partir da Beta |

---

## 7. Pipeline de ingestão CMIP6 / ESGF

Os scripts wget gerados pelo MetaGrid ESGF (presentes no projeto) listam datasets do EC-Earth3 com membros r120/r121/r132 do experimento histórico, frequência mensal (`Amon`, `Omon`, `SImon`) e variáveis diversas. Eles são o ponto de partida da ingestão. O fluxo é o seguinte:

### 7.1. Componentes

- `esgf_client.py`: parser dos scripts wget. Extrai a lista (filename, url, sha256) sem precisar executar o shell. Permite paralelizar downloads com httpx + asyncio e validar checksums em Python.
- DAG `ingest_cmip6`: três tasks principais — `fetch` (download para bronze com retries), `validate` (checksum SHA256 + abertura do NetCDF para validar metadado CF), `promote` (regrid + recorte espacial Brasil + conversão para Zarr na prata).
- Catalogação: ao final da promoção, `intake-esm` regenera o catálogo prata. Modelos consomem via catálogo, não por path direto.
- Idempotência: a DAG é safe-to-rerun. Arquivo já presente com checksum válido é pulado.

### 7.2. Esboço de implementação

```python
# src/climate_esg/ingestion/esgf_client.py
import re
from dataclasses import dataclass

@dataclass
class ESGFFile:
    filename: str
    url: str
    checksum: str
    checksum_type: str = "sha256"

LINE_RE = re.compile(
    r"'(?P<f>[^']+)'\s+'(?P<u>[^']+)'\s+'(?P<ct>[^']+)'\s+'(?P<c>[^']+)'"
)

def parse_wget_script(path: str) -> list[ESGFFile]:
    """Extract file manifest from an ESGF wget script."""
    files = []
    with open(path) as fh:
        capture = False
        for line in fh:
            if line.startswith("download_files="):
                capture = True
                continue
            if capture and line.startswith("EOF--"):
                break
            if capture:
                m = LINE_RE.search(line)
                if m:
                    files.append(ESGFFile(
                        filename=m.group("f"),
                        url=m.group("u"),
                        checksum_type=m.group("ct").lower(),
                        checksum=m.group("c"),
                    ))
    return files
```

### 7.3. Política de retenção e custo

- Bronze: retenção indefinida enquanto o storage permitir. NetCDF original é a fonte de verdade.
- Prata Zarr: regerável a partir do bronze. Pode ser limpa em casos de pressão de custo.
- Compressão: NetCDF do CMIP6 já é compactado, mas Zarr com codec Zstd reduz mais 20-30% sem perda.

### 7.4. Globus como alternativa ao wget

Para download massivo (mais de algumas centenas de gigas), Globus Transfer é mais robusto que wget — recuperação automática, paralelismo agressivo. Para o MVP, com volume ainda manejável (dezenas de GB do EC-Earth3 histórico), wget HTTPS é suficiente. Documentar a alternativa para escalar.

---

## 8. Decisões de modelo por subproblema

Cada subproblema recebe a ferramenta adequada. A tabela abaixo é a referência atualizada e ligeiramente refinada em relação à versão inicial.

| Subproblema | Modelo MVP | Evolução prevista | Métrica de aceitação |
|---|---|---|---|
| Indicadores climáticos por ativo (heat days, drought) | xclim sobre Zarr regridded | — | Reprodução de indicadores publicados (CDDI, SPEI) com erro < 1% |
| Score de risco físico | Soma ponderada de indicadores normalizados | Modelo aprendido com targets de loss histórica | Estabilidade trimestral, correlação com perdas reportadas |
| Score de risco de transição | XGBoost com SHAP | Pipeline com calibração isotônica + estabilidade | AUC > 0.75 out-of-time, Brier < 0.20 |
| Extração de metas/emissões de relatórios | SLM fine-tuned (Phi-3 mini ou Llama-3.2-3B) com saída JSON validada | Avaliar se LLM grande agrega em casos difíceis | F1 > 0.85 em campos críticos (escopo 1/2/3, target year, % redução) |
| Classificação de notícias ESG | ClimateBERT pt-BR fine-tuned + FinBERT | Active learning para reduzir custo de anotação | Macro-F1 > 0.80 em 5 classes de controvérsia |
| Projeção de impacto financeiro | DCF com fatores de cenário NGFS (R) | VaR climático com Monte Carlo | Reprodução de resultados NGFS publicados |
| Geração de explicação | Templates determinísticos + LLM para narrativa final | RAG com citação de fonte (Beta+) | Faithfulness > 0.9 (RAGAS), 100% de citação obrigatória |

---

## 9. Governança, auditoria e MLOps

### 9.1. Linhagem de dado

Cada linha em uma fato carrega `run_sk`. Cada `run_sk` aponta para: (a) commit do código, (b) versão dos dados de entrada (hash dos Parquet de ouro consumidos), (c) hiperparâmetros, (d) métricas registradas. Implementação: tabela `dim_model_run` + integração com MLflow.

### 9.2. Qualidade de dado

Great Expectations roda nas transições bronze→prata e prata→ouro. Falhas bloqueiam o pipeline. Suítes mínimas no MVP:

- Climático: valores dentro de faixas físicas plausíveis (`tasmin > -100°C`, `< 60°C`); ausência de NaN sustentado por mais de N% da série.
- Empresa: LEI/CNPJ resolvidos para 100% das companhias de carteira; setor NACE preenchido.
- Score: ausência de saltos > 30 pontos entre janelas trimestrais sem justificativa registrada.

### 9.3. Model cards e ética

Todo modelo em produção tem um model card automaticamente gerado a partir de metadados do MLflow. Inclui: dados usados, métricas em validação out-of-time, limitações conhecidas, viés esperado (especialmente para empresas pequenas e mercados emergentes), proibições de uso (ex.: não usar score isolado para decisão fiduciária).

### 9.4. CI/CD e ambientes

- Três ambientes: dev (local + docker-compose), staging (cluster reduzido em nuvem), prod (cluster com observabilidade completa).
- CI: ruff + mypy para Python, lintr para R, ESLint para frontend, pytest, Rscript de testes, build de imagens, Trivy para CVEs.
- CD: deploy automático em staging a cada merge na main; em prod com aprovação manual e tag semântica.
- Reprodutibilidade: contêineres assinados (cosign); DVC para datasets de tamanho médio; versionamento de modelos via MLflow Registry.

---

## 10. API e dashboard

### 10.1. API

FastAPI, OAuth2 com escopos por persona (acionista, analista, auditor). Resposta sempre tipada com Pydantic v2. Versionamento via prefixo (`/v1/...`). Endpoints centrais do MVP:

- `GET /v1/companies` — lista paginada com filtros por setor, país e cobertura.
- `GET /v1/companies/{lei}/scores` — todos os scores e cenários, retornando bandas e `run_sk`.
- `GET /v1/companies/{lei}/explanations/{run_sk}` — SHAP + narrativa + citações.
- `GET /v1/regions/{region_id}/scores` — score regional por cenário.
- `GET /v1/assets/{asset_id}/hazards` — exposição a hazards por cenário e horizonte.
- `POST /v1/portfolios` — registra carteira do investidor; GET retorna agregados.

### 10.2. Dashboard

React + TypeScript + Vite + Tailwind. Mapa via Mapbox GL ou Deck.gl (preferência por Deck.gl para overlays raster pesados). Recharts para gráficos. Stack pequena, deliberada — frontend não é o ponto onde inovamos.

---

## 11. Roadmap revisado e marcos

| Fase | Duração | Entregáveis técnicos | Critério de saída |
|---|---|---|---|
| F0 — Fundação | 3 semanas | Repositório monorepo, docker-compose com Postgres+PostGIS+pgvector, MinIO, Airflow; CI verde; ADRs iniciais (1-5). | `make up` traz a stack de pé; ingestão de 1 NetCDF de teste promovido até ouro. |
| F1 — MVP físico | 6 semanas | Ingestão CMIP6 completa (variáveis priorizadas); 10 empresas piloto; score físico; dashboard com mapa de exposição. | Score físico reproduzível; dashboard navegável internamente. |
| F2 — MVP transição | 5 semanas | Coletor de relatórios (CDP, formulários CVM); XGBoost de transição; SHAP no drill-down; 2 cenários NGFS aplicados. | Score composto (físico + transição) com banda de incerteza. |
| F3 — Beta | 12 semanas | Cobertura setorial ampliada; RAG sobre relatórios anuais; score regional; APIs estáveis; piloto com 1-2 investidores parceiros. | Adoção mensurada; backlog de feedback priorizado. |
| F4 — GA | 16 semanas | Agente conversacional; SSO/RBAC; SLAs definidos; observabilidade completa; documentação pública. | Lançamento comercial. |

---

## 12. Riscos atualizados

- **Engenharia de dados subestimada.** Mantido como risco #1. Mitigação: F0 dedicada exclusivamente a fundação, sem nenhum modelo.
- **Dependência de fontes ESG pagas.** Refinitiv/MSCI custam caro. Mitigação: começar com fontes públicas (CDP, B3, CVM, GLEIF, OpenCorporates) no MVP; Refinitiv só na Beta com piloto pago.
- **Custo de inferência LLM.** Mitigação: SLM local (vLLM) para 90% das tarefas; LLM grande chamada apenas em síntese final; cache agressivo.
- **Mudança regulatória ISSB / taxonomia BR.** Mitigação: camada de mapeamento metodológico externalizada em config (não em código), permitindo recalibração sem redeploy.
- **Vieses para mercados emergentes.** Mitigação: cobertura de dado tratada como atributo do score; ausência sinaliza, nunca penaliza por imputação.

---

## 13. Próximos passos imediatos

Antes de criar o repositório, confirmar três pontos:

1. **Setor do MVP.** A sugestão é agronegócio brasileiro (Raízen, SLC, BrasilAgro, Cosan, Marfrig, JBS, Minerva, M Dias Branco, Camil, São Martinho). Setor com forte exposição física, dado público suficiente, valor claro para acionistas.
2. **Stack de nuvem alvo.** AWS ou GCP. Influencia escolhas de IaC e secrets management. Para desenvolvimento local, é indiferente.
3. **Estratégia de licenciamento.** MIT/Apache 2.0 para infraestrutura e proprietária para modelos/scores, ou tudo proprietário? Define se docs/adrs ficam em repo público.

Definidos esses três pontos, o passo seguinte é criar o esqueleto do monorepo conforme seção 4, subir docker-compose, ingerir o primeiro NetCDF do EC-Earth3 e ter um exemplo end-to-end de bronze → prata → indicador climático em ouro. A partir daí o trabalho passa a ser incremental.