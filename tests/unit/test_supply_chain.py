from __future__ import annotations

from climate_esg.modeling.supply_chain import supply_chain_climate_risk

_MEANS = {"seca": 0.6, "enchente": 0.4, "deslizamento": 0.5}


def _chain():
    return {
        "cnae_codigo": "1011201",
        "division": "10",
        "upstream": [
            {"division": "01", "label": "Agropecuária"},
            {"division": None, "label": "Fornecedores de insumos e serviços"},
        ],
        "downstream": [{"division": "47", "label": "Varejo"}],
    }


def _risk(monkeypatch, means=_MEANS, **overrides):
    monkeypatch.setattr("climate_esg.modeling.supply_chain.national_hazard_means", lambda: means)
    kwargs = {
        "value_chain": _chain(),
        "company_cnae": "1011201",
        "revenue": 1_000_000_000.0,
        "ebit": 200_000_000.0,
        "ebitda": 300_000_000.0,
        "company_name": "Alimentos Teste",
    }
    kwargs.update(overrides)
    return supply_chain_climate_risk(**kwargs)


def test_sem_cadeia_no_input(monkeypatch) -> None:
    out = _risk(monkeypatch, value_chain=None)
    assert out["status"] == "no_input"
    assert "cadeia" in out["reason"]


def test_sem_receita_no_input(monkeypatch) -> None:
    for revenue in (None, 0.0):
        out = _risk(monkeypatch, revenue=revenue)
        assert out["status"] == "no_input"
        assert "receita" in out["reason"]


def test_sem_upstream_no_input(monkeypatch) -> None:
    chain = _chain()
    chain["upstream"] = []
    out = _risk(monkeypatch, value_chain=chain)
    assert out["status"] == "no_input"
    assert "montante" in out["reason"]


def test_sem_medias_nacionais_no_input(monkeypatch) -> None:
    out = _risk(monkeypatch, means={})
    assert out["status"] == "no_input"
    assert "AdaptaBrasil" in out["reason"]


def test_fonte_indisponivel_error(monkeypatch) -> None:
    def _boom():
        raise RuntimeError("timeout")

    monkeypatch.setattr("climate_esg.modeling.supply_chain.national_hazard_means", _boom)
    out = supply_chain_climate_risk(
        value_chain=_chain(),
        company_cnae="1011201",
        revenue=1_000_000_000.0,
        ebit=None,
        ebitda=None,
    )
    assert out["status"] == "error"
    assert "AdaptaBrasil indisponível" in out["reason"]


def test_ok_payload_completo(monkeypatch) -> None:
    out = _risk(monkeypatch)
    assert out["status"] == "ok"
    assert out["reason"] is None
    assert out["seal"] == "inferido"
    assert len(out["suppliers"]) == 2
    for supplier in out["suppliers"]:
        assert 0.0 <= supplier["exposure_index"] <= 100.0
        assert 0.0 <= supplier["disruption_index"] <= 100.0
        assert supplier["dominant_hazard"]
    assert 0.0 <= out["chain_risk_index"] <= 100.0
    band = out["production_at_risk_brl"]
    assert band["low"] <= band["central"] <= band["high"]
    assert out["production_at_risk_pct_ebitda"] is not None
    assert out["national_hazard_means"] == {"seca": 60.0, "enchente": 40.0, "deslizamento": 50.0}
    assert "Alimentos Teste" in out["narrative"]


def test_ok_sem_ebitda_omite_pct(monkeypatch) -> None:
    out = _risk(monkeypatch, ebitda=None)
    assert out["status"] == "ok"
    assert out["production_at_risk_pct_ebitda"] is None
