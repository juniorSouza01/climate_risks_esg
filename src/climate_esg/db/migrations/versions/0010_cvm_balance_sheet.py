"""cvm_financials: balanço (ativos totais, PL, dívida bruta)

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("cvm_financials", sa.Column("total_assets", sa.Numeric(), nullable=True))
    op.add_column("cvm_financials", sa.Column("equity", sa.Numeric(), nullable=True))
    op.add_column("cvm_financials", sa.Column("gross_debt", sa.Numeric(), nullable=True))


def downgrade() -> None:
    op.drop_column("cvm_financials", "gross_debt")
    op.drop_column("cvm_financials", "equity")
    op.drop_column("cvm_financials", "total_assets")
