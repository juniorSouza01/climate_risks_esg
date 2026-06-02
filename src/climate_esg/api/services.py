from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Session

from climate_esg.api.schemas.scores import BandOut, ScoreEntry
from climate_esg.db.models import (
    DimScenario,
    FactPhysicalRiskScore,
    FactTransitionRiskScore,
)
from climate_esg.modeling.scoring import ScoreBand, compose_score

ScoreTable = type[FactPhysicalRiskScore] | type[FactTransitionRiskScore]


def _latest_bands(
    session: Session, table: ScoreTable, company_sk: int
) -> dict[tuple[int, int], ScoreBand]:
    latest = (
        sa.select(
            table.scenario_sk,
            table.horizon_year,
            sa.func.max(table.run_sk).label("run_sk"),
        )
        .where(table.company_sk == company_sk)
        .group_by(table.scenario_sk, table.horizon_year)
        .subquery()
    )
    rows = session.execute(
        sa.select(
            table.scenario_sk,
            table.horizon_year,
            table.score_0_100,
            table.band_low,
            table.band_high,
        ).join(
            latest,
            sa.and_(
                table.scenario_sk == latest.c.scenario_sk,
                table.horizon_year == latest.c.horizon_year,
                table.run_sk == latest.c.run_sk,
            ),
        )
    ).all()
    return {
        (scen, hor): ScoreBand(central=float(c), low=float(lo), high=float(hi))
        for scen, hor, c, lo, hi in rows
    }


def _band_out(band: ScoreBand) -> BandOut:
    return BandOut(central=band.central, low=band.low, high=band.high)


def company_scores(session: Session, company_sk: int) -> list[ScoreEntry]:
    physical = _latest_bands(session, FactPhysicalRiskScore, company_sk)
    transition = _latest_bands(session, FactTransitionRiskScore, company_sk)
    scenario_names: dict[int, str] = {
        sk: name
        for sk, name in session.execute(sa.select(DimScenario.scenario_sk, DimScenario.name)).all()
    }

    entries: list[ScoreEntry] = []
    for scenario_sk, horizon_year in sorted(set(physical) | set(transition)):
        phys = physical.get((scenario_sk, horizon_year))
        trans = transition.get((scenario_sk, horizon_year))
        composite = compose_score(phys, trans) if phys and trans else None
        entries.append(
            ScoreEntry(
                scenario=scenario_names.get(scenario_sk, str(scenario_sk)),
                horizon_year=horizon_year,
                physical=_band_out(phys) if phys else None,
                transition=_band_out(trans) if trans else None,
                composite=_band_out(composite) if composite else None,
            )
        )
    return entries
