from __future__ import annotations

import datetime as dt

import pytest
import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm import Session

from climate_esg.db import seed
from climate_esg.db.base import Base
from climate_esg.db.models import (
    DimAsset,
    DimClimateVariable,
    DimCompany,
    DimDate,
    DimScenario,
)

_DIM_COMPANY_DDL = """
CREATE TABLE dim_company (
    company_sk BIGINT PRIMARY KEY,
    lei VARCHAR(20), cnpj VARCHAR(14), ticker VARCHAR(10),
    name VARCHAR(255) NOT NULL,
    sector_nace VARCHAR(10), subsector VARCHAR(50), country VARCHAR(2),
    is_listed BOOLEAN NOT NULL, market_cap_band VARCHAR(20), market_cap NUMERIC,
    validity_from DATE NOT NULL, validity_to DATE
)
"""

_DIM_ASSET_DDL = """
CREATE TABLE dim_asset (
    asset_sk BIGINT PRIMARY KEY,
    company_sk BIGINT NOT NULL REFERENCES dim_company (company_sk),
    asset_type VARCHAR(40) NOT NULL,
    name VARCHAR(255), latitude NUMERIC(9, 6), longitude NUMERIC(9, 6),
    geom TEXT,
    municipality VARCHAR(120), state VARCHAR(2), ibge_code VARCHAR(7),
    capacity NUMERIC, capex_aprox NUMERIC, opening_date DATE, status VARCHAR(20)
)
"""


@pytest.fixture()
def session():
    engine = sa.create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def _geometry_stubs(dbapi_conn, _record):
        dbapi_conn.create_function("GeomFromEWKT", 1, lambda value: value)

    Base.metadata.create_all(
        engine,
        tables=[DimScenario.__table__, DimClimateVariable.__table__, DimDate.__table__],
    )
    with engine.begin() as conn:
        conn.exec_driver_sql(_DIM_COMPANY_DDL)
        conn.exec_driver_sql(_DIM_ASSET_DDL)
    with Session(engine) as s:
        yield s
    engine.dispose()


@pytest.fixture(autouse=True)
def _short_calendar(monkeypatch):
    monkeypatch.setattr(seed, "DATE_START", dt.date(2030, 1, 1))
    monkeypatch.setattr(seed, "DATE_END", dt.date(2030, 1, 31))


def _counts(session):
    return {
        model: session.scalar(sa.select(sa.func.count()).select_from(model))
        for model in (DimScenario, DimClimateVariable, DimCompany, DimAsset, DimDate)
    }


def test_seed_twice_nao_duplica(session):
    seed.run(session=session)
    session.commit()
    first = _counts(session)
    assert first[DimCompany] == len(seed.COMPANIES)
    assert first[DimAsset] == len(seed.ASSETS)
    assert first[DimDate] == 31

    seed.run(session=session)
    session.commit()
    assert _counts(session) == first


def test_seed_nao_sobrescreve_asset_refinado(session):
    seed.run(session=session)
    session.commit()

    session.execute(
        sa.update(DimAsset)
        .where(DimAsset.asset_sk == 1)
        .values(latitude=-20.123456, longitude=-40.654321, ibge_code="3170206")
    )
    session.commit()
    session.expire_all()

    seed.run(session=session)
    session.commit()
    session.expire_all()

    row = session.execute(
        sa.select(DimAsset.latitude, DimAsset.longitude, DimAsset.ibge_code).where(
            DimAsset.asset_sk == 1
        )
    ).one()
    assert float(row.latitude) == pytest.approx(-20.123456)
    assert float(row.longitude) == pytest.approx(-40.654321)
    assert row.ibge_code == "3170206"


def test_seed_nao_sobrescreve_company_refinada(session):
    seed.run(session=session)
    session.commit()

    session.execute(
        sa.update(DimCompany).where(DimCompany.company_sk == 2).values(cnpj="84693183000168")
    )
    session.commit()
    session.expire_all()

    seed.run(session=session)
    session.commit()
    session.expire_all()

    assert (
        session.scalar(sa.select(DimCompany.cnpj).where(DimCompany.company_sk == 2))
        == "84693183000168"
    )


def test_seed_preenche_apenas_campos_nulos(session):
    seed.run(session=session)
    session.commit()

    session.execute(
        sa.update(DimAsset).where(DimAsset.asset_sk == 2).values(latitude=None, longitude=None)
    )
    session.commit()
    session.expire_all()

    seed.run(session=session)
    session.commit()
    session.expire_all()

    row = session.execute(
        sa.select(DimAsset.latitude, DimAsset.longitude).where(DimAsset.asset_sk == 2)
    ).one()
    assert float(row.latitude) == pytest.approx(seed.ASSETS[1]["latitude"])
    assert float(row.longitude) == pytest.approx(seed.ASSETS[1]["longitude"])
