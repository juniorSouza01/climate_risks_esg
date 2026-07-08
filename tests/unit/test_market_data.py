from __future__ import annotations

import httpx
import pytest

from climate_esg.ingestion import market_data
from climate_esg.ingestion.market_data import BrapiAuthError, _brapi_search


def _status_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", market_data.BRAPI_LIST_URL)
    response = httpx.Response(status, request=request)
    return httpx.HTTPStatusError(f"HTTP {status}", request=request, response=response)


def test_brapi_search_401_levanta_auth_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*_args: object, **_kwargs: object) -> object:
        raise _status_error(401)

    monkeypatch.setattr(market_data, "request_json", _raise)
    with pytest.raises(BrapiAuthError):
        _brapi_search("schulz", "tok", None)


def test_brapi_search_404_retorna_vazio(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*_args: object, **_kwargs: object) -> object:
        raise _status_error(404)

    monkeypatch.setattr(market_data, "request_json", _raise)
    assert _brapi_search("inexistente", "tok", None) == []


def test_brapi_search_ok_filtra_stocks(monkeypatch: pytest.MonkeyPatch) -> None:
    def _ok(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {"stocks": [{"stock": "SHUL4"}, {"noticker": True}]}

    monkeypatch.setattr(market_data, "request_json", _ok)
    assert _brapi_search("schulz", "tok", None) == [{"stock": "SHUL4"}]
