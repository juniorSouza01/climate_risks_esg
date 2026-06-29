from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from climate_esg.db.models import (
    DimModelRun,
    FactClimateIndicator,
    FactHazardExposure,
    FactPhysicalRiskScore,
    FactScoreExplanation,
    FactTransitionRiskScore,
)

_FACT_TABLES: dict[str, Any] = {
    "fact_climate_indicator": FactClimateIndicator,
    "fact_hazard_exposure": FactHazardExposure,
    "fact_physical_risk_score": FactPhysicalRiskScore,
    "fact_transition_risk_score": FactTransitionRiskScore,
    "fact_score_explanation": FactScoreExplanation,
}


def run_fact_counts(session: Session, run_sk: int) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name, table in _FACT_TABLES.items():
        n = session.scalar(
            sa.select(sa.func.count()).select_from(table).where(table.run_sk == run_sk)
        )
        if n:
            counts[name] = int(n)
    return counts


def list_runs(session: Session, limit: int = 100) -> list[DimModelRun]:
    return list(
        session.scalars(
            sa.select(DimModelRun).order_by(DimModelRun.run_sk.desc()).limit(limit)
        ).all()
    )
