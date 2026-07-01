"""cvm_financials por CNPJ (EBITDA, todas as cias abertas)

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cvm_financials",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("cnpj", sa.String(length=14), nullable=False),
        sa.Column("denom", sa.String(length=200), nullable=True),
        sa.Column("denom_norm", sa.String(length=200), nullable=True),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("revenue", sa.Numeric(), nullable=True),
        sa.Column("ebit", sa.Numeric(), nullable=True),
        sa.Column("ebitda", sa.Numeric(), nullable=True),
        sa.Column("net_income", sa.Numeric(), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cnpj", "fiscal_year", name="uq_cvm_financials"),
    )
    op.create_index("ix_cvm_financials_cnpj", "cvm_financials", ["cnpj"])
    op.create_index("ix_cvm_financials_denom_norm", "cvm_financials", ["denom_norm"])


def downgrade() -> None:
    op.drop_table("cvm_financials")
