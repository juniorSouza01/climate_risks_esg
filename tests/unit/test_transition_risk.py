from __future__ import annotations

import pytest

from climate_esg.modeling.transition_config import (
    COMPANY_TRANSITION_INPUTS,
    SUBSCORE_WEIGHTS,
)
from climate_esg.modeling.transition_risk import compute_transition_score


def test_pesos_somam_um() -> None:
    assert sum(SUBSCORE_WEIGHTS.values()) == pytest.approx(1.0)


def test_score_iguais_da_central_igual() -> None:
    result = compute_transition_score(50.0, 50.0, 50.0)
    assert result.band.central == pytest.approx(50.0)
    assert result.band.low == result.band.central - 5.0
    assert result.band.high == result.band.central + 5.0


def test_score_media_ponderada() -> None:
    result = compute_transition_score(100.0, 0.0, 0.0)
    assert result.band.central == pytest.approx(40.0)


def test_subscores_preservados() -> None:
    result = compute_transition_score(60.0, 55.0, 48.0)
    assert result.sub_score_policy == 60.0
    assert result.sub_score_tech == 55.0
    assert result.sub_score_market == 48.0


def test_inputs_curados_existem() -> None:
    assert set(COMPANY_TRANSITION_INPUTS) == {1, 2}
    for inp in COMPANY_TRANSITION_INPUTS.values():
        assert 0 <= inp.policy <= 100
        assert 0 <= inp.tech <= 100
        assert 0 <= inp.market <= 100
