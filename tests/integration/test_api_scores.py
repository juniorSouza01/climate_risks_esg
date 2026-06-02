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
