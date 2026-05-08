"""Testes do contrato de ScoreBand."""

from __future__ import annotations

import pytest

from climate_esg.modeling.scoring import ScoreBand, compose_score


def test_valid_band() -> None:
    b = ScoreBand(central=50, low=30, high=70)
    assert b.central == 50


def test_invalid_band_low_above_central_raises() -> None:
    with pytest.raises(ValueError):
        ScoreBand(central=10, low=20, high=50)


def test_invalid_band_high_below_central_raises() -> None:
    with pytest.raises(ValueError):
        ScoreBand(central=80, low=10, high=50)


def test_invalid_band_out_of_range_raises() -> None:
    with pytest.raises(ValueError):
        ScoreBand(central=50, low=-1, high=80)
    with pytest.raises(ValueError):
        ScoreBand(central=50, low=10, high=120)


def test_compose_default_weights() -> None:
    physical = ScoreBand(central=60, low=40, high=80)
    transition = ScoreBand(central=20, low=10, high=30)
    out = compose_score(physical, transition)
    assert out.central == pytest.approx(40.0)
    assert out.low == pytest.approx(25.0)
    assert out.high == pytest.approx(55.0)


def test_compose_invalid_weights_raise() -> None:
    p = ScoreBand(central=50, low=40, high=60)
    t = ScoreBand(central=50, low=40, high=60)
    with pytest.raises(ValueError, match="pesos"):
        compose_score(p, t, weight_physical=0.7, weight_transition=0.7)
