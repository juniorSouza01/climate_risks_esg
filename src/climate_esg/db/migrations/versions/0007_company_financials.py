"""company_financials (CVM DFP)

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "company_financials",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("company_sk", sa.BigInteger(), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("revenue", sa.Numeric(), nullable=True),
        sa.Column("net_income", sa.Numeric(), nullable=True),
        sa.Column("cnpj", sa.String(length=14), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["company_sk"], ["dim_company.company_sk"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_sk", "fiscal_year", name="uq_company_financials"),
    )
    op.create_index(
        "ix_company_financials_company_sk", "company_financials", ["company_sk"]
    )


def downgrade() -> None:
    op.drop_table("company_financials")
