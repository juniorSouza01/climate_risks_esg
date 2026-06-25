from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from climate_esg.api.main import app

pytestmark = pytest.mark.integration

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_list_companies():
    r = client.get("/v1/companies")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    assert {"company_sk", "name", "is_listed"} <= set(data[0])


def test_company_scores_structure():
    r = client.get("/v1/companies/1/scores")
    assert r.status_code == 200
    data = r.json()
    assert data["company_sk"] == 1
    assert isinstance(data["scores"], list)


def test_company_not_found():
    r = client.get("/v1/companies/999999/scores")
    assert r.status_code == 404


def test_portfolio():
    r = client.get("/v1/portfolio?scenario=historical&horizon=2030")
    assert r.status_code == 200
    data = r.json()
    assert data["scenario"] == "historical"
    assert isinstance(data["companies"], list)


def test_portfolio_cenario_inexistente():
    r = client.get("/v1/portfolio?scenario=__nope__&horizon=2030")
    assert r.status_code == 404


def test_explanations_responde():
    r = client.get("/v1/companies/1/explanations")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_transition_detail_nao_contamina_entre_empresas():
    d1 = client.get("/v1/companies/1/scores").json()
    d2 = client.get("/v1/companies/2/scores").json()
    e1 = next((s for s in d1["scores"] if s.get("transition_detail")), None)
    e2 = next((s for s in d2["scores"] if s.get("transition_detail")), None)
    if e1 and e2:
        assert e1["transition_detail"]["policy"] != e2["transition_detail"]["policy"]
