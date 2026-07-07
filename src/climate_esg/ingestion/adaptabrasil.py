from __future__ import annotations

from functools import lru_cache

import sqlalchemy as sa
from sqlalchemy.orm import Session

from climate_esg.db.models import DimAsset, DimScenario, FactHazardExposure
from climate_esg.governance.lineage import start_model_run
from climate_esg.ingestion.http import request_json
from climate_esg.quality.boundaries import validate_adaptabrasil_rows

MAPA_URL = (
    "https://sistema.adaptabrasil.mcti.gov.br/api/mapa-dados/BR/municipio/"
    "{indicator}/{year}/{scenario}/adaptabrasil"
)

INDICATOR_HAZARD = {60041: "enchente", 60001: "deslizamento", 2: "seca"}
# O id de cenário varia por família de indicador no AdaptaBrasil:
# família 60xxx usa 40 (SSP2-4.5) / 41 (SSP5-8.5); estresse hídrico (ind 2) só expõe 49.
INDICATOR_SCENARIOS: dict[int, dict[int, str]] = {
    60041: {40: "SSP2-4.5", 41: "SSP5-8.5"},
    60001: {40: "SSP2-4.5", 41: "SSP5-8.5"},
    2: {49: "SSP5-8.5"},
}
HORIZONS = (2030, 2050)
DOSSIER_YEAR = 2050
DOSSIER_SCENARIO_NAME = "SSP5-8.5"

ADAPTABRASIL_MODEL_NAME = "adaptabrasil_exposure"
ADAPTABRASIL_MODEL_VERSION = "0.2.0"


def _dossier_scenario(indicator: int) -> int | None:
    for sc_id, name in INDICATOR_SCENARIOS.get(indicator, {}).items():
        if name == DOSSIER_SCENARIO_NAME:
            return sc_id
    return None


@lru_cache(maxsize=64)
def _fetch_rows(indicator: int, year: int, scenario: int) -> tuple[tuple[str, float, str], ...]:
    payload = request_json(
        "adaptabrasil", MAPA_URL.format(indicator=indicator, year=year, scenario=scenario)
    )
    rows: list[tuple[str, float, str]] = []
    for row in payload or []:
        ibge = str(row.get("geocod_ibge", ""))
        value = row.get("value")
        if ibge and value is not None:
            try:
                rows.append((ibge, float(value), str(row.get("rangelabel") or "")))
            except (TypeError, ValueError):
                continue
    validate_adaptabrasil_rows(rows, indicator=indicator)
    return tuple(rows)


def fetch_indicator(indicator: int, year: int, scenario: int) -> dict[str, float]:
    return {ibge: value for ibge, value, _ in _fetch_rows(indicator, year, scenario)}


def municipality_risk(
    ibge_code: str, *, year: int = DOSSIER_YEAR
) -> dict[str, dict[str, float | str]]:
    out: dict[str, dict[str, float | str]] = {}
    for indicator, hazard in INDICATOR_HAZARD.items():
        scenario = _dossier_scenario(indicator)
        if scenario is None:
            continue
        for ibge, value, label in _fetch_rows(indicator, year, scenario):
            if ibge == ibge_code:
                out[hazard] = {"value": round(value, 4), "label": label}
                break
    return out


def national_hazard_means(*, year: int = DOSSIER_YEAR) -> dict[str, float]:
    out: dict[str, float] = {}
    for indicator, hazard in INDICATOR_HAZARD.items():
        scenario = _dossier_scenario(indicator)
        if scenario is None:
            continue
        rows = _fetch_rows(indicator, year, scenario)
        if rows:
            out[hazard] = round(sum(v for _, v, _ in rows) / len(rows), 4)
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
        hyperparams={
            "indicators": list(INDICATOR_HAZARD),
            "scenarios": {k: list(v) for k, v in INDICATOR_SCENARIOS.items()},
        },
    )

    written = 0
    for indicator, hazard in INDICATOR_HAZARD.items():
        for adapta_scenario, scenario_name in INDICATOR_SCENARIOS.get(indicator, {}).items():
            sk = scenario_sk.get(scenario_name)
            if sk is None:
                continue
            for year in HORIZONS:
                values = fetch_indicator(indicator, year, adapta_scenario)
                targets = [(asset_sk, values[ibge]) for asset_sk, ibge in assets if ibge in values]
                if not targets:
                    continue
                session.execute(
                    sa.delete(FactHazardExposure).where(
                        FactHazardExposure.hazard_type == hazard,
                        FactHazardExposure.scenario_sk == sk,
                        FactHazardExposure.horizon_year == year,
                        FactHazardExposure.asset_sk.in_([a for a, _ in targets]),
                    )
                )
                for asset_sk, value in targets:
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
