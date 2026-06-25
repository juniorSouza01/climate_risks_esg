"""fact_score_explanation

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fact_score_explanation",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("company_sk", sa.BigInteger(), nullable=False),
        sa.Column("scenario_sk", sa.Integer(), nullable=False),
        sa.Column("horizon_year", sa.Integer(), nullable=False),
        sa.Column("run_sk", sa.BigInteger(), nullable=False),
        sa.Column("narrative_md", sa.Text(), nullable=False),
        sa.Column("drivers", sa.JSON(), nullable=True),
        sa.Column("sources", sa.JSON(), nullable=True),
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
        "ix_fact_score_explanation_company_sk", "fact_score_explanation", ["company_sk"]
    )
    op.create_index(
        "ix_fact_score_explanation_scenario_sk", "fact_score_explanation", ["scenario_sk"]
    )


def downgrade() -> None:
    op.drop_table("fact_score_explanation")
