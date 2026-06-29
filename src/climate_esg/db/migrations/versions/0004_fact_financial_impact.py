"""fact_financial_impact

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fact_financial_impact",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("company_sk", sa.BigInteger(), nullable=False),
        sa.Column("scenario_sk", sa.Integer(), nullable=False),
        sa.Column("horizon_year", sa.Integer(), nullable=False),
        sa.Column("run_sk", sa.BigInteger(), nullable=False),
        sa.Column("dcf_adjustment_pct", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("band_low_pct", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("band_high_pct", sa.Numeric(precision=6, scale=2), nullable=False),
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
        "ix_fact_financial_impact_company_sk", "fact_financial_impact", ["company_sk"]
    )
    op.create_index(
        "ix_fact_financial_impact_scenario_sk", "fact_financial_impact", ["scenario_sk"]
    )


def downgrade() -> None:
    op.drop_table("fact_financial_impact")
