from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from climate_esg.modeling.physical_config import (
    HAZARD_WEIGHTS,
    INDICATOR_REFERENCE,
    IndicatorReference,
)
from climate_esg.modeling.scoring import ScoreBand, normalize_linear, weighted_score_band


@dataclass(frozen=True, slots=True)
class PhysicalScoreResult:
    """Resultado do score físico de uma empresa."""

    band: ScoreBand
    coverage_pct: float
    hazards: tuple[str, ...]


def compute_physical_score(
    var_means: Mapping[str, float],
    *,
    weights: Mapping[str, float] = HAZARD_WEIGHTS,
    references: Mapping[str, IndicatorReference] = INDICATOR_REFERENCE,
) -> PhysicalScoreResult:

    per_hazard: dict[str, list[float]] = defaultdict(list)
    for cf_code, value in var_means.items():
        ref = references.get(cf_code)
        if ref is None:
            continue
        per_hazard[ref.hazard].append(normalize_linear(value, ref.ref_low, ref.ref_high))

    subscores = {h: sum(vals) / len(vals) for h, vals in per_hazard.items()}
    band = weighted_score_band(subscores, weights)

    present_weight = sum(weights[h] for h in subscores if h in weights)
    total_weight = sum(weights.values())
    coverage_pct = (present_weight / total_weight * 100.0) if total_weight else 0.0

    return PhysicalScoreResult(
        band=band,
        coverage_pct=coverage_pct,
        hazards=tuple(sorted(subscores)),
    )
