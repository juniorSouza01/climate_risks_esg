"""unique constraints de grain + cache_dossier

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_GRAINS = [
    (
        "fact_climate_indicator",
        "uq_fact_climate_indicator_grain",
        ["asset_sk", "var_sk", "scenario_sk", "date_sk", "run_sk"],
    ),
    (
        "fact_physical_risk_score",
        "uq_fact_physical_risk_score_grain",
        ["company_sk", "scenario_sk", "horizon_year", "run_sk"],
    ),
    (
        "fact_transition_risk_score",
        "uq_fact_transition_risk_score_grain",
        ["company_sk", "scenario_sk", "horizon_year", "run_sk"],
    ),
    (
        "fact_financial_impact",
        "uq_fact_financial_impact_grain",
        ["company_sk", "scenario_sk", "horizon_year", "run_sk"],
    ),
    (
        "fact_score_explanation",
        "uq_fact_score_explanation_grain",
        ["company_sk", "scenario_sk", "horizon_year", "run_sk"],
    ),
    (
        "fact_hazard_exposure",
        "uq_fact_hazard_exposure_grain",
        ["asset_sk", "hazard_type", "scenario_sk", "horizon_year", "run_sk"],
    ),
]


def upgrade() -> None:
    for table, name, cols in _GRAINS:
        op.create_unique_constraint(name, table, cols)

    op.create_table(
        "cache_dossier",
        sa.Column("query_key", sa.String(length=160), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("query_key"),
    )


def downgrade() -> None:
    op.drop_table("cache_dossier")
    for table, name, _cols in _GRAINS:
        op.drop_constraint(name, table, type_="unique")
