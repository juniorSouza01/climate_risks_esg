from __future__ import annotations

import datetime as dt
import types

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from climate_esg.db.base import Base
from climate_esg.db.models import CacheDossier
from climate_esg.search import dossier as dossier_mod
from climate_esg.search.dossier import (
    DEGRADED_TTL_S,
    Dossier,
    classify_query,
    normalize_key,
    valid_cnpj,
)

VALID_CNPJ = "84693183000168"
VALID_CNPJ_MASKED = "84.693.183/0001-68"
INVALID_CNPJ = "84693183000167"


def test_valid_cnpj_digito_verificador() -> None:
    assert valid_cnpj(VALID_CNPJ) is True
    assert valid_cnpj(INVALID_CNPJ) is False
    assert valid_cnpj("11111111111111") is False
    assert valid_cnpj("123") is False
    assert valid_cnpj("8469318300016a") is False


def test_classify_query_cnpj() -> None:
    assert classify_query(VALID_CNPJ) == "cnpj"
    assert classify_query(VALID_CNPJ_MASKED) == "cnpj"
    assert classify_query(f"  {VALID_CNPJ_MASKED}  ") == "cnpj"


def test_classify_query_cnpj_invalido_vira_name() -> None:
    assert classify_query(INVALID_CNPJ) == "name"
    assert classify_query("84.693.183/0001-67") == "name"
    assert classify_query("11111111111111") == "name"


def test_classify_query_tickers() -> None:
    assert classify_query("B3SA3") == "ticker"
    assert classify_query("M1TA34") == "ticker"
    assert classify_query("PETR4") == "ticker"
    assert classify_query("petr4") == "ticker"


def test_classify_query_nome_livre() -> None:
    assert classify_query("Döhler") == "name"
    assert classify_query("Schulz S.A.") == "name"
    assert classify_query("AB") == "name"


def test_normalize_key_cnpj_mascarado_e_puro_iguais() -> None:
    assert normalize_key(VALID_CNPJ) == normalize_key(VALID_CNPJ_MASKED)
    assert normalize_key(VALID_CNPJ).endswith(f":cnpj:{VALID_CNPJ}")


def test_normalize_key_ticker_case_insensitive() -> None:
    assert normalize_key("petr4") == normalize_key("PETR4")
    assert normalize_key("PETR4").endswith(":ticker:PETR4")


def test_normalize_key_nome_colapsa_espacos() -> None:
    assert normalize_key("Schulz   do  Brasil") == normalize_key("Schulz do Brasil")
    assert normalize_key("Schulz do Brasil").endswith(":name:schulz-do-brasil")


def test_normalize_key_nome_com_cnpj_embutido_nao_colide_com_cnpj() -> None:
    name_query = f"Empresa {VALID_CNPJ} Ltda"
    assert classify_query(name_query) == "name"
    assert ":cnpj:" not in normalize_key(name_query)
    assert normalize_key(name_query) != normalize_key(VALID_CNPJ)


class _Clock:
    current = dt.datetime(2026, 1, 1, 12, 0, 0)

    @classmethod
    def now(cls, tz=None):
        return cls.current


@pytest.fixture()
def session():
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine, tables=[CacheDossier.__table__])
    with Session(engine) as s:
        yield s
    engine.dispose()


@pytest.fixture()
def patched(monkeypatch):
    _Clock.current = dt.datetime(2026, 1, 1, 12, 0, 0)
    monkeypatch.setattr(
        dossier_mod,
        "dt",
        types.SimpleNamespace(datetime=_Clock, UTC=dt.UTC, timedelta=dt.timedelta),
    )
    builds = {"count": 0, "errors": []}

    def _fake_build(query: str, *, max_news: int = 25) -> Dossier:
        builds["count"] += 1
        return Dossier(query=query, kind="name", name=query, errors=list(builds["errors"]))

    monkeypatch.setattr(dossier_mod, "build_dossier", _fake_build)
    monkeypatch.setattr(dossier_mod, "_resolve_company_sk", lambda session, query, d: None)
    monkeypatch.setattr(dossier_mod, "_attach_financials", lambda session, d, cnpj: None)
    monkeypatch.setattr(dossier_mod, "_attach_analytics", lambda session, d, cnpj: None)
    monkeypatch.setattr(dossier_mod, "_attach_climate_financial", lambda d: None)
    monkeypatch.setattr(dossier_mod, "_attach_relationships", lambda d, cnpj: None)
    monkeypatch.setattr(dossier_mod, "_attach_supply_chain", lambda d: None)
    return builds


def test_cache_hit_dentro_do_ttl(session, patched) -> None:
    first = dossier_mod.get_or_build_dossier(session, "Empresa Teste", ttl_s=3600)
    assert first["cached"] is False
    assert patched["count"] == 1

    second = dossier_mod.get_or_build_dossier(session, "Empresa Teste", ttl_s=3600)
    assert second["cached"] is True
    assert patched["count"] == 1

    row = session.get(CacheDossier, normalize_key("Empresa Teste"))
    assert (row.expires_at - _Clock.current).total_seconds() == pytest.approx(3600)


def test_cache_expira_apos_ttl(session, patched) -> None:
    dossier_mod.get_or_build_dossier(session, "Empresa Teste", ttl_s=3600)
    _Clock.current += dt.timedelta(seconds=3601)
    rebuilt = dossier_mod.get_or_build_dossier(session, "Empresa Teste", ttl_s=3600)
    assert rebuilt["cached"] is False
    assert patched["count"] == 2


def test_dossie_degradado_usa_ttl_curto(session, patched) -> None:
    patched["errors"].append({"source": "gdelt", "code": "timeout", "transient": True})
    payload = dossier_mod.get_or_build_dossier(session, "Empresa Degradada", ttl_s=3600)
    assert payload["status"] == "degraded"

    row = session.get(CacheDossier, normalize_key("Empresa Degradada"))
    assert (row.expires_at - _Clock.current).total_seconds() == pytest.approx(DEGRADED_TTL_S)

    _Clock.current += dt.timedelta(seconds=DEGRADED_TTL_S + 1)
    rebuilt = dossier_mod.get_or_build_dossier(session, "Empresa Degradada", ttl_s=3600)
    assert rebuilt["cached"] is False
    assert patched["count"] == 2
