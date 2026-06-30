from __future__ import annotations

from functools import lru_cache

import sqlalchemy as sa
from sqlalchemy.orm import Session

from climate_esg.db.models import DimAsset, DimScenario, FactHazardExposure
from climate_esg.governance.lineage import start_model_run
from climate_esg.ingestion.http import get_client

MAPA_URL = (
    "https://sistema.adaptabrasil.mcti.gov.br/api/mapa-dados/BR/municipio/"
    "{indicator}/{year}/{scenario}/adaptabrasil"
)

INDICATOR_HAZARD = {60041: "enchente", 60001: "deslizamento"}
SCENARIO_MAP = {40: "SSP2-4.5", 41: "SSP5-8.5"}
HORIZONS = (2030, 2050)
DOSSIER_YEAR = 2050
DOSSIER_SCENARIO = 41

ADAPTABRASIL_MODEL_NAME = "adaptabrasil_exposure"
ADAPTABRASIL_MODEL_VERSION = "0.1.0"


@lru_cache(maxsize=64)
def _fetch_rows(indicator: int, year: int, scenario: int) -> tuple[tuple[str, float, str], ...]:
    resp = get_client().get(
        MAPA_URL.format(indicator=indicator, year=year, scenario=scenario), timeout=90.0
    )
    resp.raise_for_status()
    rows: list[tuple[str, float, str]] = []
    for row in resp.json():
        ibge = str(row.get("geocod_ibge", ""))
        value = row.get("value")
        if ibge and value is not None:
            try:
                rows.append((ibge, float(value), str(row.get("rangelabel") or "")))
            except (TypeError, ValueError):
                continue
    return tuple(rows)


def fetch_indicator(indicator: int, year: int, scenario: int) -> dict[str, float]:
    return {ibge: value for ibge, value, _ in _fetch_rows(indicator, year, scenario)}


def municipality_risk(
    ibge_code: str, *, year: int = DOSSIER_YEAR, scenario: int = DOSSIER_SCENARIO
) -> dict[str, dict[str, float | str]]:
    out: dict[str, dict[str, float | str]] = {}
    for indicator, hazard in INDICATOR_HAZARD.items():
        for ibge, value, label in _fetch_rows(indicator, year, scenario):
            if ibge == ibge_code:
                out[hazard] = {"value": round(value, 4), "label": label}
                break
    return out


def ingest_adaptabrasil_exposure(session: Session) -> int:
    assets = [
        (sk, str(ibge))
        for sk, ibge in session.execute(
            sa.select(DimAsset.asset_sk, DimAsset.ibge_code).where(DimAsset.ibge_code.is_not(None))
        ).all()
    ]
    if not assets:
        return 0

    scenario_sk = {
        name: sk
        for sk, name in session.execute(sa.select(DimScenario.scenario_sk, DimScenario.name)).all()
    }

    run_sk = start_model_run(
        session,
        model_name=ADAPTABRASIL_MODEL_NAME,
        model_version=ADAPTABRASIL_MODEL_VERSION,
        hyperparams={"indicators": list(INDICATOR_HAZARD), "scenarios": list(SCENARIO_MAP)},
    )

    written = 0
    for indicator, hazard in INDICATOR_HAZARD.items():
        for adapta_scenario, scenario_name in SCENARIO_MAP.items():
            sk = scenario_sk.get(scenario_name)
            if sk is None:
                continue
            for year in HORIZONS:
                values = fetch_indicator(indicator, year, adapta_scenario)
                for asset_sk, ibge in assets:
                    value = values.get(ibge)
                    if value is None:
                        continue
                    session.add(
                        FactHazardExposure(
                            asset_sk=asset_sk,
                            hazard_type=hazard,
                            scenario_sk=sk,
                            horizon_year=year,
                            run_sk=run_sk,
                            exposure_normalized=round(value, 4),
                        )
                    )
                    written += 1
    return written
