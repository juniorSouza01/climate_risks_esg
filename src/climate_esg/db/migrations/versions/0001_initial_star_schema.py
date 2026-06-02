"""initial star schema

Cria o star schema do MVP (project.md §6.2): dimensões compartilhadas e as
três fatos atuais. Geometrias via PostGIS (índices GIST explícitos). Demais
fatos (hazard_exposure, score_explanation, news_signal) entram em F1/F2.

Revision ID: 0001
Revises:
Create Date: 2026-06-01
"""

from __future__ import annotations

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostGIS é pré-requisito das colunas Geometry. init_db.sh já cria, mas
    # repetimos de forma idempotente para a stack de CI funcionar sozinha.
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # ---- dim_company -----------------------------------------------------
    op.create_table(
        "dim_company",
        sa.Column("company_sk", sa.BigInteger(), nullable=False),
        sa.Column("lei", sa.String(length=20), nullable=True),
        sa.Column("cnpj", sa.String(length=14), nullable=True),
        sa.Column("ticker", sa.String(length=10), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sector_nace", sa.String(length=10), nullable=True),
        sa.Column("subsector", sa.String(length=50), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("is_listed", sa.Boolean(), nullable=False),
        sa.Column("market_cap_band", sa.String(length=20), nullable=True),
        sa.Column("validity_from", sa.Date(), nullable=False),
        sa.Column("validity_to", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("company_sk"),
        sa.UniqueConstraint("lei", "validity_from", name="uq_dim_company_lei_from"),
    )
    op.create_index("ix_dim_company_lei", "dim_company", ["lei"])
    op.create_index("ix_dim_company_cnpj", "dim_company", ["cnpj"])
    op.create_index("ix_dim_company_ticker", "dim_company", ["ticker"])

    # ---- dim_asset -------------------------------------------------------
    op.create_table(
        "dim_asset",
        sa.Column("asset_sk", sa.BigInteger(), nullable=False),
        sa.Column("company_sk", sa.BigInteger(), nullable=False),
        sa.Column("asset_type", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="POINT", srid=4326, spatial_index=False, from_text="ST_GeomFromEWKT", name="geometry"
            ),
            nullable=True,
        ),
        sa.Column("municipality", sa.String(length=120), nullable=True),
        sa.Column("state", sa.String(length=2), nullable=True),
        sa.Column("capacity", sa.Numeric(), nullable=True),
        sa.Column("capex_aprox", sa.Numeric(), nullable=True),
        sa.Column("opening_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(
            ["company_sk"], ["dim_company.company_sk"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("asset_sk"),
    )
    op.create_index("ix_dim_asset_company_sk", "dim_asset", ["company_sk"])
    op.create_index(
        "idx_dim_asset_geom", "dim_asset", ["geom"], postgresql_using="gist"
    )

    # ---- dim_region ------------------------------------------------------
    op.create_table(
        "dim_region",
        sa.Column("region_sk", sa.BigInteger(), nullable=False),
        sa.Column("iso_country", sa.String(length=2), nullable=False),
        sa.Column("admin1", sa.String(length=60), nullable=True),
        sa.Column("admin2", sa.String(length=120), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False, from_text="ST_GeomFromEWKT", name="geometry"
            ),
            nullable=True,
        ),
        sa.Column("hierarchy_path", sa.Text(), nullable=True),
        sa.Column("population", sa.BigInteger(), nullable=True),
        sa.Column("gdp", sa.Numeric(), nullable=True),
        sa.PrimaryKeyConstraint("region_sk"),
    )
    op.create_index("ix_dim_region_iso_country", "dim_region", ["iso_country"])
    op.create_index(
        "idx_dim_region_geom", "dim_region", ["geom"], postgresql_using="gist"
    )

    # ---- dim_date --------------------------------------------------------
    op.create_table(
        "dim_date",
        sa.Column("date_sk", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("quarter", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("is_br_fiscal_year_end", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("date_sk"),
    )
    op.create_index("ix_dim_date_date", "dim_date", ["date"], unique=True)

    # ---- dim_scenario ----------------------------------------------------
    op.create_table(
        "dim_scenario",
        sa.Column("scenario_sk", sa.Integer(), nullable=False),
        sa.Column("framework", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("horizon_year", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=120), nullable=True),
        sa.Column("version", sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint("scenario_sk"),
        sa.UniqueConstraint("name"),
    )

    # ---- dim_climate_variable -------------------------------------------
    op.create_table(
        "dim_climate_variable",
        sa.Column("var_sk", sa.Integer(), nullable=False),
        sa.Column("cf_code", sa.String(length=40), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_model", sa.String(length=60), nullable=True),
        sa.Column("source_experiment", sa.String(length=60), nullable=True),
        sa.Column("source_member", sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint("var_sk"),
        sa.UniqueConstraint("cf_code"),
    )

    # ---- dim_model_run ---------------------------------------------------
    op.create_table(
        "dim_model_run",
        sa.Column("run_sk", sa.BigInteger(), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("model_version", sa.String(length=40), nullable=False),
        sa.Column("code_commit", sa.String(length=40), nullable=True),
        sa.Column("train_data_version", sa.String(length=80), nullable=True),
        sa.Column("train_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hyperparams", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("run_sk"),
    )
    op.create_index("ix_dim_model_run_model_name", "dim_model_run", ["model_name"])
    op.create_index("ix_dim_model_run_code_commit", "dim_model_run", ["code_commit"])

    # ---- fact_climate_indicator -----------------------------------------
    op.create_table(
        "fact_climate_indicator",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("asset_sk", sa.BigInteger(), nullable=False),
        sa.Column("var_sk", sa.Integer(), nullable=False),
        sa.Column("scenario_sk", sa.Integer(), nullable=False),
        sa.Column("date_sk", sa.Integer(), nullable=False),
        sa.Column("run_sk", sa.BigInteger(), nullable=False),
        sa.Column("value_mean", sa.Numeric(), nullable=True),
        sa.Column("value_max", sa.Numeric(), nullable=True),
        sa.Column("value_min", sa.Numeric(), nullable=True),
        sa.Column("anomaly_vs_baseline", sa.Numeric(), nullable=True),
        sa.Column("percentile", sa.Numeric(), nullable=True),
        sa.ForeignKeyConstraint(["asset_sk"], ["dim_asset.asset_sk"]),
        sa.ForeignKeyConstraint(["var_sk"], ["dim_climate_variable.var_sk"]),
        sa.ForeignKeyConstraint(["scenario_sk"], ["dim_scenario.scenario_sk"]),
        sa.ForeignKeyConstraint(["date_sk"], ["dim_date.date_sk"]),
        sa.ForeignKeyConstraint(["run_sk"], ["dim_model_run.run_sk"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_fact_climate_indicator_asset_sk", "fact_climate_indicator", ["asset_sk"]
    )
    op.create_index(
        "ix_fact_climate_indicator_var_sk", "fact_climate_indicator", ["var_sk"]
    )
    op.create_index(
        "ix_fact_climate_indicator_scenario_sk",
        "fact_climate_indicator",
        ["scenario_sk"],
    )
    op.create_index(
        "ix_fact_climate_indicator_date_sk", "fact_climate_indicator", ["date_sk"]
    )

    # ---- fact_physical_risk_score ---------------------------------------
    op.create_table(
        "fact_physical_risk_score",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("company_sk", sa.BigInteger(), nullable=False),
        sa.Column("scenario_sk", sa.Integer(), nullable=False),
        sa.Column("horizon_year", sa.Integer(), nullable=False),
        sa.Column("run_sk", sa.BigInteger(), nullable=False),
        sa.Column("score_0_100", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("band_low", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("band_high", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("n_assets", sa.Integer(), nullable=False),
        sa.Column("coverage_pct", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["company_sk"], ["dim_company.company_sk"]),
        sa.ForeignKeyConstraint(["scenario_sk"], ["dim_scenario.scenario_sk"]),
        sa.ForeignKeyConstraint(["run_sk"], ["dim_model_run.run_sk"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_fact_physical_risk_score_company_sk",
        "fact_physical_risk_score",
        ["company_sk"],
    )
    op.create_index(
        "ix_fact_physical_risk_score_scenario_sk",
        "fact_physical_risk_score",
        ["scenario_sk"],
    )

    # ---- fact_transition_risk_score -------------------------------------
    op.create_table(
        "fact_transition_risk_score",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("company_sk", sa.BigInteger(), nullable=False),
        sa.Column("scenario_sk", sa.Integer(), nullable=False),
        sa.Column("horizon_year", sa.Integer(), nullable=False),
        sa.Column("run_sk", sa.BigInteger(), nullable=False),
        sa.Column("score_0_100", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("band_low", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("band_high", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("carbon_intensity", sa.Numeric(), nullable=True),
        sa.Column("target_alignment", sa.Numeric(), nullable=True),
        sa.Column("sub_score_policy", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("sub_score_tech", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("sub_score_market", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["company_sk"], ["dim_company.company_sk"]),
        sa.ForeignKeyConstraint(["scenario_sk"], ["dim_scenario.scenario_sk"]),
        sa.ForeignKeyConstraint(["run_sk"], ["dim_model_run.run_sk"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_fact_transition_risk_score_company_sk",
        "fact_transition_risk_score",
        ["company_sk"],
    )
    op.create_index(
        "ix_fact_transition_risk_score_scenario_sk",
        "fact_transition_risk_score",
        ["scenario_sk"],
    )


def downgrade() -> None:
    op.drop_table("fact_transition_risk_score")
    op.drop_table("fact_physical_risk_score")
    op.drop_table("fact_climate_indicator")
    op.drop_table("dim_model_run")
    op.drop_table("dim_climate_variable")
    op.drop_table("dim_scenario")
    op.drop_table("dim_date")
    op.drop_index("idx_dim_region_geom", table_name="dim_region")
    op.drop_table("dim_region")
    op.drop_index("idx_dim_asset_geom", table_name="dim_asset")
    op.drop_table("dim_asset")
    op.drop_table("dim_company")
