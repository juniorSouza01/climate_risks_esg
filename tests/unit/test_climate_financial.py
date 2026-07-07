from __future__ import annotations

import pytest

from climate_esg.modeling.climate_financial import climate_financial_impact, sector_profile


def _impact(**overrides):
    kwargs = {
        "cnae_code": "1011201",
        "climate_index": 50.0,
        "revenue": 1_000_000_000.0,
        "ebit": 200_000_000.0,
        "ebitda": 300_000_000.0,
        "total_assets": 2_000_000_000.0,
        "company_name": "Alimentos Teste",
    }
    kwargs.update(overrides)
    return climate_financial_impact(**kwargs)


def test_sem_indice_climatico_no_input() -> None:
    out = _impact(climate_index=None)
    assert out["status"] == "no_input"
    assert "índice climático" in out["reason"]
    assert "channels" not in out


def test_sem_receita_no_input() -> None:
    for revenue in (None, 0.0, -10.0):
        out = _impact(revenue=revenue)
        assert out["status"] == "no_input"
        assert "receita" in out["reason"]


def test_ok_payload_completo() -> None:
    out = _impact()
    assert out["status"] == "ok"
    assert out["reason"] is None
    assert out["sector"]["division"] == "10"
    assert out["sector"]["archetype"] == "Alimentos"
    assert out["sector"]["assumed"] is False
    assert out["physical_exposure"] == pytest.approx(0.5)
    assert out["seal"] == "inferido"
    assert set(out["channels"]) == {"receita", "materia_prima", "ebitda", "ativos", "roi"}
    assert isinstance(out["narrative"], str) and "Alimentos Teste" in out["narrative"]


def test_ok_canais_coerentes() -> None:
    out = _impact()
    receita = out["channels"]["receita"]["brl"]
    assert receita["central"] == pytest.approx(1_000_000_000.0 * 0.5 * 0.10)
    assert receita["low"] <= receita["central"] <= receita["high"]

    materia = out["channels"]["materia_prima"]["brl"]
    assert materia["central"] == pytest.approx(800_000_000.0 * 0.5 * 0.22)

    for channel in ("receita", "materia_prima", "ebitda", "ativos"):
        band = out["channels"][channel]["brl"]
        assert band["low"] <= band["central"] <= band["high"]


def test_ok_risco_ajustado_limitado_e_rotulado() -> None:
    out = _impact()
    risco = out["risco_ajustado"]
    assert 0.0 <= risco["value"] <= 100.0
    assert risco["value"] == pytest.approx(67.2, abs=0.1)
    assert risco["label"] == "alto"
    assert 0.0 <= out["materialidade"] <= 1.0

    saturado = _impact(climate_index=100.0, ebitda=1_000.0)
    assert saturado["risco_ajustado"]["value"] <= 100.0


def test_setor_desconhecido_usa_perfil_default() -> None:
    out = _impact(cnae_code="9911001")
    assert out["status"] == "ok"
    assert out["sector"]["archetype"] == "Setor geral"
    assert out["sector"]["assumed"] is True


def test_sector_profile_sem_cnae() -> None:
    prof = sector_profile(None)
    assert prof["division"] is None
    assert prof["assumed"] is True
    assert prof["archetype"] == "Setor geral"
