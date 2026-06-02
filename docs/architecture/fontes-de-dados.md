# Fontes de Dados, Tratamento e Objetivo

> Onde os dados entram, como são tratados (bronze→prata→ouro) e onde queremos chegar.
> Reconciliado com [`project.md`](../source/project.md) §6–§7 e [ADR-0004](../adrs/0004-piloto-n2-deep-dive.md)/[ADR-0005](../adrs/0005-perfil-hazard-joinville.md).
> Substitui parcialmente o `data_dictionary.md` previsto no doc.

---

## 1. Objetivo do tratamento

Transformar dados heterogêneos (climáticos raster, financeiros, ESG textuais, geoespaciais) em um **star schema auditável** na camada ouro, do qual saem **scores de risco físico e de transição com banda de incerteza**, sempre rastreáveis via `run_sk`. O fluxo é unidirecional e sem atalhos:

```
Fonte externa → BRONZE (bruto) → PRATA (limpo, padronizado, chave canônica) → OURO (fatos/features) → Score → API → Dashboard
```

Regra de ouro (§3.2): **nenhum componente de modelagem grava em bronze/prata**. Todo writeback (scores, explicações, runs) vai para tabelas próprias, preservando a linhagem da origem.

---

## 2. Camadas do data lake (local, sem MinIO — ADR-0002)

| Camada | Conteúdo | Formato | Partição | Local |
|---|---|---|---|---|
| **Bronze** | Bruto como recebido: NetCDF CMIP6, PDFs, JSON de APIs, CSV | original | por fonte + data ingestão | `data/bronze/` |
| **Prata** | Limpo, padronizado, chave canônica; raster regridded | Parquet (tabular), **Zarr** (raster) | por entidade + ano | `data/silver/` |
| **Ouro** | Fatos/features modelados (star schema) | Parquet + tabelas Postgres | por modelo de consumo | `data/gold/` + Postgres |

Layout DRS do CMIP6 bronze (já implementado em `utils/storage.py`):
`data/bronze/cmip6/EC-Earth3/historical/r120i1p1f1/Amon/tasmin/gr/v20200412/`

---

## 3. Fonte 1 — Climática: CMIP6 via ESGF *(núcleo do risco físico)*

### 3.1. O que já temos (baixado/catalogado)
- **Modelo:** EC-Earth3 (EC-Earth-Consortium).
- **Experimento:** `historical`.
- **Membros:** `r120i1p1f1`, `r121i1p1f1`, `r132i1p1f1`.
- **Frequência:** mensal (`Amon` atmosfera, `Omon` oceano, `SImon` gelo).
- **Manifestos:** 10 scripts wget em [`data/manifests/cmip6_wget/`](../../data/manifests/cmip6_wget) — **450 arquivos `.nc`** catalogados.
- **Variáveis presentes (grade `gr`):** `tasmin`, `hurs`, `hus`, `huss`, `prsn`, `rsdt` (+ `uo`, `sivol` em grade oceânica). Cada arquivo cobre 1 ano: `<var>_<tabela>_EC-Earth3_historical_<membro>_gr_YYYY01-YYYY12.nc`.
- **Relevância para Joinville/SC:** `tasmin` (calor/frio) é a útil hoje. `prsn`/`sivol`/`uo`/`rsdt` têm baixa relevância industrial em SC.

### 3.2. O que falta obter *(F1 — ADR-0005)*
Nova requisição MetaGrid ESGF, arquivar com prefixo `v2_`:
- **Variáveis:** `pr` (precipitação — enchente), `tasmax` (calor extremo), `sfcWindmax` (vento extremo).
- **Experimentos:** `historical` + `ssp245` (SSP2-4.5) + `ssp585` (SSP5-8.5).
- **Modelo:** EC-Earth3 (principal); avaliar MPI-ESM1-2-HR / CMCC-ESM2 como secundário p/ incerteza inter-modelo (F2).

### 3.3. Tratamento (bronze → prata → ouro)
1. **Bronze:** `fetch` baixa o `.nc` original, valida **SHA256**, idempotente. *(implementado)*
2. **Validate:** abre com xarray + cf-xarray; checa variável/unidade/dims CF e ranges físicos (`-100°C < tasmin < 60°C`). *(a implementar)*
3. **Prata:** regrid para grade comum, recorte espacial SC/Brasil, escrita **Zarr** (codec Zstd, -20-30%). Catálogo via `intake-esm`. *(a implementar)*
4. **Ouro:** índices climáticos com **xclim** (Rx5day, R99pTOT, TX90p, WSDI, dias > 32°C) → `fact_climate_indicator` (asset × var × cenário × tempo). *(a implementar)*

### 3.4. Validação independente
Reanálise **ERA5** como benchmark histórico de calibração do regridding (não dá projeção — só validação). Estações **INMET** locais para aferir downscaling.

---

## 4. Fonte 2 — Geoespacial: ativos e regiões *(exposição)*

| Fonte | Uso | Destino |
|---|---|---|
| **IBGE** | malha municipal de Joinville/SC, censo, geografia | `dim_region` (PostGIS MULTIPOLYGON) |
| Coordenadas das plantas Döhler/Schulz | lat/long dos ativos industriais | `dim_asset` (PostGIS POINT) |
| **CPRM** | cartas de suscetibilidade a deslizamento (Joinville) | overlay de hazard |
| **ANA** | séries hidrológicas bacia Itapocu/Cachoeira | hazard enchente |
| **CEMADEN** | alertas históricos de chuva/deslizamento em SC | validação de sinal |
| **Defesa Civil SC (S2iD)** | registros oficiais de eventos (cheias 2008/2011/2017) | validação de coerência |

**Tratamento:** geometrias validadas em PostGIS (índice GIST em `geom`); exposição via `ST_Intersects`/buffers (raster hazard × ativo) → `fact_hazard_exposure`.

---

## 5. Fonte 3 — Financeira/ESG corporativa *(risco de transição — F2)*

Perfil **assimétrico** das duas empresas (ADR-0004):

| Empresa | Tipo | Fontes disponíveis |
|---|---|---|
| **Schulz S.A.** (B3: SHUL3/SHUL4) | capital aberto | **CVM** (formulários, ITR/DFP), **B3**, Yahoo Finance, relatórios anuais, CDP (se reportar) |
| **Döhler S.A.** | capital fechado | relatórios voluntários, **GHG Protocol BR**, CDP (se reportar), CNAE/CNPJ públicos — **sem CVM/B3** |

**Fontes públicas (MVP):** CDP, B3, CVM, **GLEIF** (LEI), **OpenCorporates**. Refinitiv/MSCI só na Beta (pagas — risco #2).

**Tratamento:** `filings_parser.py` (PDF→texto→JSON validado via SLM), resolução de identidade LEI/CNPJ → `dim_company` (SCD2). Métricas (intensidade de carbono, alinhamento de metas) viram sub-scores ponderados em `fact_transition_risk_score`.

---

## 6. Fonte 4 — Notícias / sinal ESG *(F2/F3)*
- **GDELT**, RSS, scrapers controlados → `news_collector.py`.
- Classificação ClimateBERT pt-BR + FinBERT → `fact_news_signal` (sentimento, controvérsia, contagem).

---

## 7. Fonte 5 — Cenários e parâmetros metodológicos
- **NGFS / IPCC SSP** → `dim_scenario` (SSP2-4.5, SSP5-8.5, historical).
- **Pesos de score** (físico por hazard; transição por sub-score) externalizados em **config**, não em código — permite recalibração sem redeploy (mitiga risco regulatório ISSB/taxonomia BR).
- Cada recálculo gera novo `run_sk` em `dim_model_run` (commit + hash do dado + params).

---

## 8. Qualidade de dado (Great Expectations / Pandera)

Roda **nas transições** bronze→prata e prata→ouro; falha **bloqueia** o pipeline. Suítes mínimas do MVP:

- **Climático:** faixas físicas plausíveis; sem NaN sustentado acima de N% da série.
- **Empresa:** LEI/CNPJ resolvidos para 100% da carteira; setor preenchido.
- **Score:** sem salto > 30 pontos entre trimestres sem justificativa registrada.

---

## 9. Onde queremos chegar (visão do dado pronto)

Para **Döhler** e **Schulz**, em cada cenário (historical/SSP2-4.5/SSP5-8.5) e horizonte (2030/2040/2050):

1. **Indicadores climáticos por ativo** (`fact_climate_indicator`) — calor, chuva extrema, vento.
2. **Exposição a hazard por planta** (`fact_hazard_exposure`) — enchente, deslizamento, vento, calor.
3. **Score físico por empresa** com banda (`fact_physical_risk_score`).
4. **Score de transição por empresa** com banda (`fact_transition_risk_score`).
5. **Score composto** com banda + **explicação** (`fact_score_explanation`).
6. Tudo **auditável** (`run_sk`) e exposto via **API** → **dashboard** (heatmap, drill-down, mapa).

> Critério de coerência (ADR-0004): a enchente de 2017 em Joinville deve elevar o score físico das duas empresas. Cobertura de dado é **atributo** do score — ausência sinaliza, nunca penaliza por imputação (mitiga viés de mercado emergente).
