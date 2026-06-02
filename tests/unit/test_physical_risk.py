"""Testes da engine pura de score físico e dos helpers de scoring."""

from __future__ import annotations

import pytest

from climate_esg.modeling.physical_config import HAZARD_WEIGHTS
from climate_esg.modeling.physical_risk import compute_physical_score
from climate_esg.modeling.scoring import (
    ScoreBand,
    clamp,
    normalize_linear,
    weighted_score_band,
)

# ---- helpers puros -------------------------------------------------------


def test_clamp() -> None:
    assert clamp(5, 0, 10) == 5
    assert clamp(-1, 0, 10) == 0
    assert clamp(11, 0, 10) == 10


def test_normalize_linear_basico() -> None:
    assert normalize_linear(0, 0, 100) == 0
    assert normalize_linear(50, 0, 100) == 50
    assert normalize_linear(100, 0, 100) == 100


def test_normalize_linear_clampeia() -> None:
    assert normalize_linear(-10, 0, 100) == 0
    assert normalize_linear(200, 0, 100) == 100


def test_normalize_linear_faixa_invertida() -> None:
    # menor valor = pior (100)
    assert normalize_linear(0, 100, 0) == 100
    assert normalize_linear(100, 100, 0) == 0


def test_normalize_linear_ref_degenerada() -> None:
    assert normalize_linear(42, 10, 10) == 50.0


def test_weighted_score_band_central_e_banda() -> None:
    weights = {"a": 0.5, "b": 0.5}
    band = weighted_score_band(
        {"a": 80, "b": 40}, weights, base_uncertainty=0.0, coverage_penalty=0.0
    )
    assert band.central == pytest.approx(60.0)  # média ponderada
    # spread = (80-40)/2 = 20 → banda 60±20
    assert band.low == pytest.approx(40.0)
    assert band.high == pytest.approx(80.0)


def test_weighted_score_band_cobertura_parcial_alarga() -> None:
    weights = {"a": 0.5, "b": 0.5}
    # só 'a' presente → cobertura 0.5 → penalidade 0.5*coverage_penalty
    band = weighted_score_band({"a": 50}, weights, base_uncertainty=0.0, coverage_penalty=20.0)
    assert band.central == pytest.approx(50.0)
    assert band.high - band.central == pytest.approx(10.0)  # (1-0.5)*20


def test_weighted_score_band_sem_match_levanta() -> None:
    with pytest.raises(ValueError, match="nenhum sub-score"):
        weighted_score_band({"x": 50}, {"a": 1.0})


def test_weighted_score_band_retorna_scoreband() -> None:
    band = weighted_score_band({"a": 50}, {"a": 1.0})
    assert isinstance(band, ScoreBand)


# ---- compute_physical_score ---------------------------------------------


def test_compute_physical_score_mapeia_e_pontua() -> None:
    # tasmax médio 313.15K (40°C) → calor=100; pr 1e-4 → enchente=100.
    result = compute_physical_score({"tasmax": 313.15, "pr": 1.0e-4})
    assert result.band.central == pytest.approx(100.0)
    assert set(result.hazards) == {"calor", "enchente"}
    # cobertura = (0.25 calor + 0.35 enchente) / 1.0 = 60%
    assert result.coverage_pct == pytest.approx(60.0)


def test_compute_physical_score_ignora_variavel_sem_referencia() -> None:
    # rsdt não mapeia hazard → sem sub-score → ValueError.
    with pytest.raises(ValueError):
        compute_physical_score({"rsdt": 400.0})


def test_compute_physical_score_pesos_somam_um() -> None:
    assert sum(HAZARD_WEIGHTS.values()) == pytest.approx(1.0)


def test_compute_physical_score_duas_vars_mesmo_hazard_media() -> None:
    # tasmax(40°C→100) e tasmin(25°C→100) ambos calor → subscore calor=100.
    result = compute_physical_score({"tasmax": 313.15, "tasmin": 298.15})
    assert result.hazards == ("calor",)
    assert result.band.central == pytest.approx(100.0)
