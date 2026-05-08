"""ORM SQLAlchemy 2.x do star schema (project.md §6.2).

MVP cobre as dimensões compartilhadas e duas fatos centrais
(fact_climate_indicator, fact_physical_risk_score). Demais fatos serão
adicionados nas fases F1/F2 conforme entrarem em uso.

Nomenclatura:
- Surrogate keys terminam em ``_sk`` (BIGINT autoincrement).
- Toda fato carrega ``run_sk`` ligando a uma execução em ``dim_model_run``
  (princípio de auditabilidade §2.2.2).
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from climate_esg.db.base import Base

# ---------------------------------------------------------------------------
# Dimensões compartilhadas
# ---------------------------------------------------------------------------


class DimCompany(Base):
    """Empresas cobertas. SCD Tipo 2 via validity_from/validity_to."""

    __tablename__ = "dim_company"
    __table_args__ = (
        UniqueConstraint("lei", "validity_from", name="uq_dim_company_lei_from"),
    )

    company_sk: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    lei: Mapped[str | None] = mapped_column(String(20), index=True)
    cnpj: Mapped[str | None] = mapped_column(String(14), index=True)
    ticker: Mapped[str | None] = mapped_column(String(10), index=True)
    name: Mapped[str] = mapped_column(String(255))
    sector_nace: Mapped[str | None] = mapped_column(String(10))
    subsector: Mapped[str | None] = mapped_column(String(50))
    country: Mapped[str | None] = mapped_column(String(2))
    is_listed: Mapped[bool] = mapped_column(Boolean, default=False)
    market_cap_band: Mapped[str | None] = mapped_column(String(20))
    validity_from: Mapped[dt.date] = mapped_column(Date)
    validity_to: Mapped[dt.date | None] = mapped_column(Date, nullable=True)

    assets: Mapped[list["DimAsset"]] = relationship(back_populates="company")


class DimAsset(Base):
    """Ativos físicos georreferenciados."""

    __tablename__ = "dim_asset"

    asset_sk: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    company_sk: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dim_company.company_sk", ondelete="RESTRICT"), index=True
    )
    asset_type: Mapped[str] = mapped_column(String(40))  # planta, fazenda, escritorio
    name: Mapped[str | None] = mapped_column(String(255))
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    geom = mapped_column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    municipality: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(2))
    capacity: Mapped[float | None] = mapped_column(Numeric)
    capex_aprox: Mapped[float | None] = mapped_column(Numeric)
    opening_date: Mapped[dt.date | None] = mapped_column(Date)
    status: Mapped[str | None] = mapped_column(String(20))

    company: Mapped[DimCompany] = relationship(back_populates="assets")


class DimRegion(Base):
    """Regiões administrativas e geometrias agregadas."""

    __tablename__ = "dim_region"

    region_sk: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    iso_country: Mapped[str] = mapped_column(String(2), index=True)
    admin1: Mapped[str | None] = mapped_column(String(60))  # estado/UF
    admin2: Mapped[str | None] = mapped_column(String(120))  # município
    geom = mapped_column(Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=True)
    hierarchy_path: Mapped[str | None] = mapped_column(Text)
    population: Mapped[int | None] = mapped_column(BigInteger)
    gdp: Mapped[float | None] = mapped_column(Numeric)


class DimDate(Base):
    """Calendário pré-populado (BR fiscal-aware)."""

    __tablename__ = "dim_date"

    date_sk: Mapped[int] = mapped_column(Integer, primary_key=True)  # YYYYMMDD
    date: Mapped[dt.date] = mapped_column(Date, unique=True, index=True)
    year: Mapped[int] = mapped_column(Integer)
    quarter: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    day_of_week: Mapped[int] = mapped_column(Integer)
    is_br_fiscal_year_end: Mapped[bool] = mapped_column(Boolean, default=False)


class DimScenario(Base):
    """Cenários climáticos (NGFS, IPCC SSP)."""

    __tablename__ = "dim_scenario"

    scenario_sk: Mapped[int] = mapped_column(Integer, primary_key=True)
    framework: Mapped[str] = mapped_column(String(20))  # NGFS / IPCC
    name: Mapped[str] = mapped_column(String(60), unique=True)  # SSP2-4.5, NetZero2050, ...
    horizon_year: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(120))
    version: Mapped[str | None] = mapped_column(String(20))


class DimClimateVariable(Base):
    """Variáveis CF do CMIP6 e equivalentes."""

    __tablename__ = "dim_climate_variable"

    var_sk: Mapped[int] = mapped_column(Integer, primary_key=True)
    cf_code: Mapped[str] = mapped_column(String(40), unique=True)  # tas, tasmin, pr, ...
    unit: Mapped[str | None] = mapped_column(String(40))
    description: Mapped[str | None] = mapped_column(Text)
    source_model: Mapped[str | None] = mapped_column(String(60))  # EC-Earth3
    source_experiment: Mapped[str | None] = mapped_column(String(60))
    source_member: Mapped[str | None] = mapped_column(String(20))


class DimModelRun(Base):
    """Cada execução de modelo. Coluna obrigatória em todas as fatos."""

    __tablename__ = "dim_model_run"

    run_sk: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(120), index=True)
    model_version: Mapped[str] = mapped_column(String(40))
    code_commit: Mapped[str | None] = mapped_column(String(40), index=True)
    train_data_version: Mapped[str | None] = mapped_column(String(80))
    train_date: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    hyperparams: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ---------------------------------------------------------------------------
# Fatos (subset MVP)
# ---------------------------------------------------------------------------


class FactClimateIndicator(Base):
    """Indicadores climáticos por ativo × variável × cenário × tempo."""

    __tablename__ = "fact_climate_indicator"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    asset_sk: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dim_asset.asset_sk"), index=True
    )
    var_sk: Mapped[int] = mapped_column(
        Integer, ForeignKey("dim_climate_variable.var_sk"), index=True
    )
    scenario_sk: Mapped[int] = mapped_column(
        Integer, ForeignKey("dim_scenario.scenario_sk"), index=True
    )
    date_sk: Mapped[int] = mapped_column(Integer, ForeignKey("dim_date.date_sk"), index=True)
    run_sk: Mapped[int] = mapped_column(BigInteger, ForeignKey("dim_model_run.run_sk"))
    value_mean: Mapped[float | None] = mapped_column(Numeric)
    value_max: Mapped[float | None] = mapped_column(Numeric)
    value_min: Mapped[float | None] = mapped_column(Numeric)
    anomaly_vs_baseline: Mapped[float | None] = mapped_column(Numeric)
    percentile: Mapped[float | None] = mapped_column(Numeric)


class FactPhysicalRiskScore(Base):
    """Score físico por empresa × cenário × horizonte × run."""

    __tablename__ = "fact_physical_risk_score"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    company_sk: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dim_company.company_sk"), index=True
    )
    scenario_sk: Mapped[int] = mapped_column(
        Integer, ForeignKey("dim_scenario.scenario_sk"), index=True
    )
    horizon_year: Mapped[int] = mapped_column(Integer)
    run_sk: Mapped[int] = mapped_column(BigInteger, ForeignKey("dim_model_run.run_sk"))
    score_0_100: Mapped[float] = mapped_column(Numeric(6, 2))
    band_low: Mapped[float] = mapped_column(Numeric(6, 2))
    band_high: Mapped[float] = mapped_column(Numeric(6, 2))
    n_assets: Mapped[int] = mapped_column(Integer)
    coverage_pct: Mapped[float] = mapped_column(Numeric(5, 2))
    computed_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class FactTransitionRiskScore(Base):
    """Score de transição. No MVP é soma ponderada (ADR-0004), não XGBoost."""

    __tablename__ = "fact_transition_risk_score"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    company_sk: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dim_company.company_sk"), index=True
    )
    scenario_sk: Mapped[int] = mapped_column(
        Integer, ForeignKey("dim_scenario.scenario_sk"), index=True
    )
    horizon_year: Mapped[int] = mapped_column(Integer)
    run_sk: Mapped[int] = mapped_column(BigInteger, ForeignKey("dim_model_run.run_sk"))
    score_0_100: Mapped[float] = mapped_column(Numeric(6, 2))
    band_low: Mapped[float] = mapped_column(Numeric(6, 2))
    band_high: Mapped[float] = mapped_column(Numeric(6, 2))
    carbon_intensity: Mapped[float | None] = mapped_column(Numeric)
    target_alignment: Mapped[float | None] = mapped_column(Numeric)
    sub_score_policy: Mapped[float | None] = mapped_column(Numeric(6, 2))
    sub_score_tech: Mapped[float | None] = mapped_column(Numeric(6, 2))
    sub_score_market: Mapped[float | None] = mapped_column(Numeric(6, 2))
    computed_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
