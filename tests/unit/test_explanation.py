from __future__ import annotations

from climate_esg.modeling.explanation import build_narrative, risk_label
from climate_esg.modeling.scoring import ScoreBand


def test_risk_label() -> None:
    assert risk_label(10) == "baixo"
    assert risk_label(50) == "moderado"
    assert risk_label(80) == "alto"


def test_narrative_completa() -> None:
    n = build_narrative(
        company_name="Empresa X",
        scenario="historical",
        horizon_year=2030,
        physical=ScoreBand(central=60, low=40, high=80),
        transition=ScoreBand(central=50, low=40, high=60),
        composite=ScoreBand(central=55, low=40, high=70),
        sub_scores={"policy": 58.0, "tech": 52.0, "market": 48.0},
        coverage_pct=25.0,
    )
    assert "Empresa X" in n.text
    assert "55/100" in n.text
    assert n.drivers["pilar_dominante"] == "físico"
    assert n.drivers["sub_score_dominante"]["chave"] == "policy"
    assert n.drivers["coverage_pct"] == 25.0


def test_narrative_transicao_dominante() -> None:
    n = build_narrative(
        company_name="Y",
        scenario="historical",
        horizon_year=2040,
        physical=ScoreBand(central=30, low=20, high=40),
        transition=ScoreBand(central=70, low=60, high=80),
        composite=ScoreBand(central=50, low=40, high=60),
        sub_scores={"policy": 40.0, "tech": 80.0, "market": 50.0},
        coverage_pct=80.0,
    )
    assert n.drivers["pilar_dominante"] == "transição"
    assert n.drivers["sub_score_dominante"]["chave"] == "tech"


def test_narrative_sem_dados_nao_quebra() -> None:
    n = build_narrative(
        company_name="Z",
        scenario="s",
        horizon_year=2050,
        physical=None,
        transition=None,
        composite=None,
        sub_scores={},
        coverage_pct=0.0,
    )
    assert "Z" in n.text
    assert n.drivers["pilar_dominante"] is None
