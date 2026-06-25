"""fact_hazard_exposure

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fact_hazard_exposure",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("asset_sk", sa.BigInteger(), nullable=False),
        sa.Column("hazard_type", sa.String(length=40), nullable=False),
        sa.Column("scenario_sk", sa.Integer(), nullable=False),
        sa.Column("horizon_year", sa.Integer(), nullable=False),
        sa.Column("run_sk", sa.BigInteger(), nullable=False),
        sa.Column("exposure_normalized", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("return_period", sa.Numeric(), nullable=True),
        sa.Column("capex_fraction_at_risk", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["asset_sk"], ["dim_asset.asset_sk"]),
        sa.ForeignKeyConstraint(["scenario_sk"], ["dim_scenario.scenario_sk"]),
        sa.ForeignKeyConstraint(["run_sk"], ["dim_model_run.run_sk"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fact_hazard_exposure_asset_sk", "fact_hazard_exposure", ["asset_sk"])
    op.create_index(
        "ix_fact_hazard_exposure_hazard_type", "fact_hazard_exposure", ["hazard_type"]
    )
    op.create_index(
        "ix_fact_hazard_exposure_scenario_sk", "fact_hazard_exposure", ["scenario_sk"]
    )


def downgrade() -> None:
    op.drop_table("fact_hazard_exposure")
