from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from climate_esg.modeling.scoring import ScoreBand

SCENARIO_MAX_IMPACT: dict[str, float] = {
    "historical": 0.10,
    "SSP2-4.5": 0.20,
    "SSP5-8.5": 0.35,
}

DEFAULT_MAX_IMPACT = 0.15


@dataclass(frozen=True, slots=True)
class FinancialImpact:
    dcf_adjustment_pct: float
    band_low_pct: float
    band_high_pct: float


def compute_financial_impact(
    composite: ScoreBand,
    *,
    scenario: str,
    max_impact: Mapping[str, float] = SCENARIO_MAX_IMPACT,
) -> FinancialImpact:
    factor = max_impact.get(scenario, DEFAULT_MAX_IMPACT)
    central = -(composite.central / 100.0) * factor * 100.0
    band_low = -(composite.high / 100.0) * factor * 100.0
    band_high = -(composite.low / 100.0) * factor * 100.0
    return FinancialImpact(
        dcf_adjustment_pct=round(central, 2),
        band_low_pct=round(band_low, 2),
        band_high_pct=round(band_high, 2),
    )
