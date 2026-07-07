from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from climate_esg.modeling.scoring import (
    ScoreBand,
    compose_score,
    normalize_linear,
    weighted_score_band,
)

_HAZARDS = ("enchente", "calor", "vento", "deslizamento")

values = st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False)
scores_0_100 = st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)
positive_weights = st.floats(min_value=0.01, max_value=10.0, allow_nan=False, allow_infinity=False)


@st.composite
def weights_and_subscores(draw):
    weights = draw(
        st.dictionaries(st.sampled_from(_HAZARDS), positive_weights, min_size=1, max_size=4)
    )
    present = draw(
        st.lists(st.sampled_from(sorted(weights)), min_size=1, max_size=len(weights), unique=True)
    )
    subscores = {h: draw(scores_0_100) for h in present}
    return weights, subscores


@st.composite
def score_bands(draw):
    a = draw(scores_0_100)
    b = draw(scores_0_100)
    c = draw(scores_0_100)
    low, central, high = sorted((a, b, c))
    return ScoreBand(central=central, low=low, high=high)


@given(value=values, ref_low=values, ref_high=values)
def test_normalize_linear_em_0_100(value, ref_low, ref_high):
    out = normalize_linear(value, ref_low, ref_high)
    assert 0.0 <= out <= 100.0


@given(v1=values, v2=values, ref_low=values, ref_high=values)
def test_normalize_linear_monotonica(v1, v2, ref_low, ref_high):
    if ref_low >= ref_high:
        ref_low, ref_high = ref_high, ref_low + 1.0
    lo, hi = sorted((v1, v2))
    assert normalize_linear(lo, ref_low, ref_high) <= normalize_linear(hi, ref_low, ref_high)


@given(value=values, ref=values)
def test_normalize_linear_sem_faixa_retorna_50(value, ref):
    assert normalize_linear(value, ref, ref) == 50.0


@given(data=weights_and_subscores())
def test_weighted_score_band_respeita_banda(data):
    weights, subscores = data
    band = weighted_score_band(subscores, weights)
    assert 0.0 <= band.low <= band.central <= band.high <= 100.0


@given(data=weights_and_subscores())
def test_weighted_score_band_central_dentro_dos_subscores(data):
    weights, subscores = data
    band = weighted_score_band(subscores, weights)
    assert min(subscores.values()) - 1e-9 <= band.central <= max(subscores.values()) + 1e-9


@given(physical=score_bands(), transition=score_bands(), w=st.floats(min_value=0.0, max_value=1.0))
def test_compose_score_respeita_banda(physical, transition, w):
    band = compose_score(physical, transition, weight_physical=w, weight_transition=1.0 - w)
    assert 0.0 <= band.low <= band.central <= band.high <= 100.0


@given(
    c1=scores_0_100,
    c2=scores_0_100,
    t=scores_0_100,
    w=st.floats(min_value=0.0, max_value=1.0),
)
def test_compose_score_monotonico_no_pilar_fisico(c1, c2, t, w):
    lo, hi = sorted((c1, c2))
    transition = ScoreBand(central=t, low=t, high=t)
    out_lo = compose_score(
        ScoreBand(central=lo, low=lo, high=lo),
        transition,
        weight_physical=w,
        weight_transition=1.0 - w,
    )
    out_hi = compose_score(
        ScoreBand(central=hi, low=hi, high=hi),
        transition,
        weight_physical=w,
        weight_transition=1.0 - w,
    )
    assert out_lo.central <= out_hi.central + 1e-9
