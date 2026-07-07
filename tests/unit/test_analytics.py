from __future__ import annotations

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from climate_esg.db.base import Base
from climate_esg.db.models import CvmFinancials
from climate_esg.modeling.analytics import analyze_company

TARGET_CNPJ = "84693183000168"
TARGET_CNPJ_MASKED = "84.693.183/0001-68"

_CLIMATE_RISK = {
    "enchente": {"value": 0.8, "label": "alto"},
    "seca": {"value": 0.5, "label": "médio"},
    "deslizamento": {"value": 0.2, "label": "baixo"},
}


@pytest.fixture()
def session():
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine, tables=[CvmFinancials.__table__])
    with Session(engine) as s:
        yield s
    engine.dispose()


def _seed_universe(session: Session, n: int) -> None:
    for i in range(n):
        cnpj = TARGET_CNPJ if i == 0 else f"{i:014d}"
        revenue = 10 ** (7 + (i % 6) * 0.5)
        session.add(
            CvmFinancials(
                id=i + 1,
                cnpj=cnpj,
                denom=f"EMPRESA {i} S.A.",
                denom_norm=f"EMPRESA {i}",
                fiscal_year=2024,
                revenue=revenue,
                ebitda=revenue * (0.10 + (i % 5) * 0.04),
                net_income=revenue * (0.02 + (i % 4) * 0.03),
                source="cvm_dfp_2024",
            )
        )
    session.commit()


def test_universo_insuficiente(session) -> None:
    _seed_universe(session, 5)
    out = analyze_company(session, TARGET_CNPJ)
    assert out["status"] == "insufficient_universe"
    assert "mínimo" in out["reason"]
    assert "cross" not in out


def test_cnpj_com_e_sem_mascara_mesma_empresa(session) -> None:
    _seed_universe(session, 24)
    masked = analyze_company(session, TARGET_CNPJ_MASKED, climate_risk=_CLIMATE_RISK)
    plain = analyze_company(session, TARGET_CNPJ, climate_risk=_CLIMATE_RISK)
    assert masked["status"] == plain["status"] == "ok"
    assert masked["cross"]["revenue_percentile"] == plain["cross"]["revenue_percentile"]
    assert masked["cross"]["ebitda_margin_percentile"] == plain["cross"]["ebitda_margin_percentile"]
    assert masked["predictions"]["segment"] == plain["predictions"]["segment"]
    assert masked["predictions"]["peers"] == plain["predictions"]["peers"]


def test_ok_payload_completo(session) -> None:
    _seed_universe(session, 24)
    out = analyze_company(session, TARGET_CNPJ, name="Empresa Zero", climate_risk=_CLIMATE_RISK)
    assert out["status"] == "ok"
    assert out["reason"] is None

    cross = out["cross"]
    assert cross["climate_index"]["value"] == pytest.approx(54.5)
    assert cross["climate_index"]["label"] == "médio"
    rar = cross["revenue_at_risk"]
    assert rar["pct_low"] <= rar["pct_central"] <= rar["pct_high"]
    assert rar["brl_low"] <= rar["brl_central"] <= rar["brl_high"]
    assert 0.0 <= cross["revenue_percentile"]["value"] <= 100.0
    assert cross["revenue_percentile"]["n"] == 24
    assert "Empresa Zero" in cross["narrative"]

    predictions = out["predictions"]
    assert predictions["segment"]["n_total"] == 24
    assert predictions["segment"]["n_in_cluster"] >= 1
    assert len(predictions["peers"]["items"]) >= 1
    assert all(p["cnpj"] != TARGET_CNPJ for p in predictions["peers"]["items"])
    assert isinstance(predictions["anomaly"]["is_outlier"], bool)


def test_fora_do_universo_com_receita_externa(session) -> None:
    _seed_universe(session, 12)
    out = analyze_company(
        session, None, name="Empresa Fechada", climate_risk=_CLIMATE_RISK, revenue=5e8
    )
    assert out["status"] == "ok"
    assert out["cross"]["revenue_percentile"]["n"] == 12
    assert "revenue_at_risk" in out["cross"]
    assert out["predictions"] == {}


def test_sem_cnpj_sem_receita_sem_clima(session) -> None:
    _seed_universe(session, 12)
    out = analyze_company(session, None)
    assert out["status"] == "ok"
    assert "climate_index" not in out["cross"]
    assert "revenue_percentile" not in out["cross"]
    assert out["predictions"] == {}
