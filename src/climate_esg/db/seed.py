"""Seed das dimensões-base do MVP.

Idempotente: pode rodar várias vezes (usa surrogate keys fixas + merge para as
dimensões pequenas e insere apenas datas ausentes em ``dim_date``).

Popula o mínimo para o pipeline E2E ter chaves:
- ``dim_scenario``      — historical, SSP2-4.5, SSP5-8.5.
- ``dim_climate_variable`` — variáveis CF priorizadas para Joinville/SC (ADR-0005).
- ``dim_company``       — Döhler e Schulz (ADR-0004).
- ``dim_asset``         — plantas em Joinville/SC (coords aproximadas, refinar em F1).
- ``dim_date``          — calendário diário 1988–2050 (BR fiscal-aware).

Uso:
    climate-esg db seed
    # ou
    python -m climate_esg.db.seed
"""

from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
from geoalchemy2.elements import WKTElement
from sqlalchemy.orm import Session

from climate_esg.db.base import session_scope
from climate_esg.db.models import (
    DimAsset,
    DimClimateVariable,
    DimCompany,
    DimDate,
    DimScenario,
)
from climate_esg.logging import get_logger

log = get_logger(__name__)

# CMIP6 historical começa em 1850; cenários SSP vão até 2100. Cobrimos a janela
# inteira para não descartar dados de baseline históricos na materialização.
DATE_START = dt.date(1850, 1, 1)
DATE_END = dt.date(2100, 12, 31)


# ---------------------------------------------------------------------------
# Conteúdo do seed
# ---------------------------------------------------------------------------

SCENARIOS: list[dict[str, object]] = [
    {
        "scenario_sk": 1,
        "framework": "IPCC",
        "name": "historical",
        "horizon_year": None,
        "description": "Experimento histórico CMIP6 (calibração de baseline).",
        "source": "CMIP6 CMIP",
        "version": "6",
    },
    {
        "scenario_sk": 2,
        "framework": "IPCC",
        "name": "SSP2-4.5",
        "horizon_year": None,
        "description": "Cenário intermediário (ScenarioMIP ssp245).",
        "source": "CMIP6 ScenarioMIP",
        "version": "6",
    },
    {
        "scenario_sk": 3,
        "framework": "IPCC",
        "name": "SSP5-8.5",
        "horizon_year": None,
        "description": "Cenário alto (ScenarioMIP ssp585).",
        "source": "CMIP6 ScenarioMIP",
        "version": "6",
    },
]

# (var_sk, cf_code, unidade, descrição). EC-Earth3 como fonte (ADR-0005).
# 1-6: prioritárias p/ hazards de SC. 7-9: presentes nos manifests atuais
# (historical já baixado) — incluídas para o smoke test E2E funcionar com
# qualquer um dos 10 wget scripts.
CLIMATE_VARIABLES: list[tuple[int, str, str, str]] = [
    (1, "tasmin", "K", "Temperatura mínima do ar a 2m."),
    (2, "tasmax", "K", "Temperatura máxima (calor extremo)."),
    (3, "pr", "kg m-2 s-1", "Precipitação total (enchente)."),
    (4, "sfcWindmax", "m s-1", "Vento máximo (vento extremo)."),
    (5, "hurs", "%", "Umidade relativa à superfície."),
    (6, "huss", "1", "Umidade específica à superfície."),
    (7, "rsdt", "W m-2", "Radiação solar incidente no topo da atmosfera."),
    (8, "prsn", "kg m-2 s-1", "Precipitação de neve (baixa relevância em SC)."),
    (9, "hus", "1", "Umidade específica (níveis de pressão)."),
]

# ADR-0004: Döhler (capital fechado) e Schulz (B3 SHUL3/SHUL4). LEI/CNPJ a
# resolver via GLEIF/OpenCorporates (US 6.1.1) — deixados nulos por ora.
COMPANIES: list[dict[str, object]] = [
    {
        "company_sk": 1,
        "lei": None,
        "cnpj": None,
        "ticker": None,
        "name": "Döhler S.A.",
        "sector_nace": "13",  # têxtil
        "subsector": "têxtil cama/mesa/banho",
        "country": "BR",
        "is_listed": False,
        "market_cap_band": None,
        "validity_from": dt.date(2026, 1, 1),
        "validity_to": None,
    },
    {
        "company_sk": 2,
        "lei": None,
        "cnpj": None,
        "ticker": "SHUL4",
        "name": "Schulz S.A.",
        "sector_nace": "28",  # máquinas e equipamentos / autopeças
        "subsector": "compressores e autopeças",
        "country": "BR",
        "is_listed": True,
        "market_cap_band": None,
        "validity_from": dt.date(2026, 1, 1),
        "validity_to": None,
    },
]

# Coordenadas APROXIMADAS (Joinville/SC). Refinar com geocoding oficial em F1
# (US 4.2.1 / runbook data_sources). Não usar para decisão sem refino.
ASSETS: list[dict[str, object]] = [
    {
        "asset_sk": 1,
        "company_sk": 1,
        "asset_type": "planta",
        "name": "Döhler — planta Joinville",
        "latitude": -26.3045,
        "longitude": -48.8487,
        "municipality": "Joinville",
        "state": "SC",
        "status": "ativo",
    },
    {
        "asset_sk": 2,
        "company_sk": 2,
        "asset_type": "planta",
        "name": "Schulz — planta Joinville",
        "latitude": -26.2710,
        "longitude": -48.8460,
        "municipality": "Joinville",
        "state": "SC",
        "status": "ativo",
    },
]


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------


def _seed_scenarios(session: Session) -> None:
    for row in SCENARIOS:
        session.merge(DimScenario(**row))


def _seed_climate_variables(session: Session) -> None:
    for var_sk, cf_code, unit, description in CLIMATE_VARIABLES:
        session.merge(
            DimClimateVariable(
                var_sk=var_sk,
                cf_code=cf_code,
                unit=unit,
                description=description,
                source_model="EC-Earth3",
                source_experiment="historical",
                source_member="r120i1p1f1",
            )
        )


def _seed_companies(session: Session) -> None:
    for row in COMPANIES:
        session.merge(DimCompany(**row))


def _seed_assets(session: Session) -> None:
    for row in ASSETS:
        data = dict(row)
        lat, lon = data["latitude"], data["longitude"]
        data["geom"] = WKTElement(f"POINT({lon} {lat})", srid=4326)
        session.merge(DimAsset(**data))


def _seed_dates(session: Session) -> int:
    """Insere apenas as datas ausentes entre DATE_START e DATE_END."""
    existing: set[int] = set(session.scalars(sa.select(DimDate.date_sk)).all())
    rows: list[dict[str, object]] = []
    cur = DATE_START
    one_day = dt.timedelta(days=1)
    while cur <= DATE_END:
        date_sk = cur.year * 10000 + cur.month * 100 + cur.day
        if date_sk not in existing:
            rows.append(
                {
                    "date_sk": date_sk,
                    "date": cur,
                    "year": cur.year,
                    "quarter": (cur.month - 1) // 3 + 1,
                    "month": cur.month,
                    "day_of_week": cur.weekday(),  # 0 = segunda
                    "is_br_fiscal_year_end": cur.month == 12 and cur.day == 31,
                }
            )
        cur += one_day
    if rows:
        session.execute(sa.insert(DimDate), rows)
    return len(rows)


def run() -> None:
    """Roda o seed completo de forma idempotente."""
    with session_scope() as session:
        _seed_scenarios(session)
        _seed_climate_variables(session)
        _seed_companies(session)
        _seed_assets(session)
        n_dates = _seed_dates(session)
    log.info(
        "db.seed.done",
        scenarios=len(SCENARIOS),
        climate_variables=len(CLIMATE_VARIABLES),
        companies=len(COMPANIES),
        assets=len(ASSETS),
        dates_inserted=n_dates,
    )


if __name__ == "__main__":
    run()
