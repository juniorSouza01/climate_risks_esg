from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping

from climate_esg.modeling.physical_config import INDICATOR_REFERENCE, IndicatorReference
from climate_esg.modeling.scoring import normalize_linear


def asset_hazard_exposures(
    var_means: Mapping[str, float],
    *,
    references: Mapping[str, IndicatorReference] = INDICATOR_REFERENCE,
) -> dict[str, float]:
    per_hazard: dict[str, list[float]] = defaultdict(list)
    for cf_code, value in var_means.items():
        ref = references.get(cf_code)
        if ref is None:
            continue
        per_hazard[ref.hazard].append(normalize_linear(value, ref.ref_low, ref.ref_high) / 100.0)
    return {hazard: sum(vals) / len(vals) for hazard, vals in per_hazard.items()}
