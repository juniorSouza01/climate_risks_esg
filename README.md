# Plataforma de Análise de Riscos Climáticos para ESG

> **Proprietary — All Rights Reserved.**
> © 2026 Osney Andrade de Souza Junior. Não distribuir, reproduzir ou criar obras derivadas sem autorização escrita do autor.

Plataforma de análise de riscos climáticos físicos e de transição para suporte à decisão de investimento ESG, alinhada a TCFD, ISSB IFRS S2 e cenários NGFS/IPCC.

A documentação técnica autoritativa está em [`docs/source/project.md`](docs/source/project.md) (versão 2.0). Decisões que divergem do documento estão registradas como ADRs em [`docs/adrs/`](docs/adrs/).

---

## Status

**Fase F0 — Fundação (3 semanas).** Repositório recém-criado. Stack local sem Docker; orquestração via Prefect 3; banco Postgres 16 + PostGIS 3 + pgvector instalados nativamente.

Empresas piloto: **Döhler** e **Schulz** (Joinville/SC). Hazards prioritários: enchentes, deslizamentos, ventos extremos, calor extremo urbano.

---

## Pré-requisitos

- **Linux** (testado em Ubuntu/Mint 6.17+)
- **Python 3.11** (gerenciado por [`uv`](https://docs.astral.sh/uv/))
- **R 4.4+** (gerenciado por `renv`, opcional na F0)
- **PostgreSQL 16** + **PostGIS 3** + **pgvector** (nativos, ver [`infra/local/`](infra/local/))
- **Node 20+** (apenas para o frontend, fora do escopo F0)

Sem Docker. Por decisão arquitetural — ver [`docs/adrs/0002-no-docker-local.md`](docs/adrs/0002-no-docker-local.md).

---

## Quick start

```bash
# 1. Clonar e entrar no repo
cd climate-esg-platform

# 2. Instalar uv (se ainda não tem)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Instalar dependências Python
make install-dev

# 4. Configurar .env
cp .env.example .env
# (edite as credenciais)

# 5. Instalar Postgres+PostGIS+pgvector nativos
make setup-system

# 6. Inicializar database (role, db, extensões)
make db-init

# 7. Aplicar schema e popular dimensões-base
make db-migrate   # cria as tabelas do star schema (Alembic)
make db-seed      # cenários, variáveis CF, Döhler/Schulz, ativos, calendário

# 8. Verificar saúde
make check        # lint + typecheck + tests
```

---

## Estrutura

```
climate-esg-platform/
├── src/
│   ├── climate_esg/        # Pacote Python principal
│   │   ├── ingestion/      # Coletores (ESGF/CMIP6, CDP, B3, CVM, GDELT)
│   │   ├── geospatial/     # raster, exposição, regridding
│   │   ├── modeling/       # físico, transição, scoring, financeiro
│   │   ├── nlp/            # extractors, classifiers, RAG (Beta+)
│   │   ├── governance/     # linhagem, model cards, auditoria
│   │   ├── api/            # FastAPI
│   │   ├── db/             # SQLAlchemy + Alembic
│   │   ├── cli/            # Typer CLIs
│   │   └── utils/
│   ├── r_analytics/        # R: econometria, validação independente
│   └── frontend/           # React + TS (vazio na F0)
├── pipelines/              # Prefect 3 flows + deployments
├── infra/local/            # Scripts apt/SQL para Postgres nativo
├── data/                   # bronze/silver/gold (gitignored) + manifests
│   └── manifests/
│       └── cmip6_wget/     # Scripts wget originais do MetaGrid ESGF
├── tests/                  # unit, integration, fixtures
├── docs/
│   ├── source/             # Documentação fonte (project.md, info.md)
│   ├── adrs/               # Architecture Decision Records
│   ├── architecture/
│   └── runbooks/
├── notebooks/              # Exploratórios
├── pyproject.toml          # Deps Python (uv)
├── Makefile                # Atalhos
└── .env.example
```

---

## Comandos úteis

| Comando | O que faz |
|---|---|
| `make help` | Lista todos os alvos |
| `make install-dev` | Instala deps com extras de dev |
| `make setup-system` | Instala Postgres+PostGIS+pgvector via apt |
| `make db-init` | Cria role/db e extensões |
| `make prefect-server` | Sobe Prefect UI em :4200 |
| `make api` | Sobe FastAPI em :8000 |
| `make check` | Lint + types + tests |
| `make test-cov` | Tests com cobertura HTML em `htmlcov/` |

---

## Princípios não negociáveis

Reproduzidos de [`docs/source/project.md`](docs/source/project.md) §2.2:

1. **Modelos especializados calculam, LLM apenas comunica e extrai.** Nenhum score numérico final é produzido por LLM.
2. **Tudo é auditável.** Cada score tem `run_sk` ligando dado, código, parâmetros, métricas.
3. **Reprodutibilidade reforçada.** Dado versionado + código versionado + ambiente versionado.
4. **Bandas de incerteza explícitas.** Score é faixa, nunca ponto único.
5. **Comece simples.** Soma ponderada antes de XGBoost; XGBoost antes de redes; foundation models só com ganho mensurável.

---

## Licença

Proprietária. Ver topo deste arquivo.
