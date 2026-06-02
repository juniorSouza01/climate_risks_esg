from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from climate_esg.modeling.scoring import ScoreBand, weighted_score_band
from climate_esg.modeling.transition_config import SUBSCORE_WEIGHTS


@dataclass(frozen=True, slots=True)
class TransitionScoreResult:
    band: ScoreBand
    sub_score_policy: float
    sub_score_tech: float
    sub_score_market: float


def compute_transition_score(
    policy: float,
    tech: float,
    market: float,
    *,
    weights: Mapping[str, float] = SUBSCORE_WEIGHTS,
) -> TransitionScoreResult:
    subscores = {"policy": policy, "tech": tech, "market": market}
    band = weighted_score_band(subscores, weights)
    return TransitionScoreResult(
        band=band,
        sub_score_policy=policy,
        sub_score_tech=tech,
        sub_score_market=market,
    )
