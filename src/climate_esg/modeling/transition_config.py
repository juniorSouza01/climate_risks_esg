from __future__ import annotations

from dataclasses import dataclass

SUBSCORE_WEIGHTS: dict[str, float] = {
    "policy": 0.40,
    "tech": 0.35,
    "market": 0.25,
}

TRANSITION_MODEL_NAME = "transition_weighted_sum"
TRANSITION_MODEL_VERSION = "0.1.0"


@dataclass(frozen=True, slots=True)
class TransitionInput:
    policy: float
    tech: float
    market: float
    carbon_intensity: float | None = None
    target_alignment: float | None = None


COMPANY_TRANSITION_INPUTS: dict[int, TransitionInput] = {
    1: TransitionInput(
        policy=58.0,
        tech=52.0,
        market=48.0,
        carbon_intensity=0.80,
        target_alignment=0.40,
    ),
    2: TransitionInput(
        policy=46.0,
        tech=50.0,
        market=49.0,
        carbon_intensity=0.60,
        target_alignment=0.60,
    ),
}
