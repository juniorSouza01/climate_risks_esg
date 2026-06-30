"""dim_asset.ibge_code

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("dim_asset", sa.Column("ibge_code", sa.String(length=7), nullable=True))
    op.create_index("ix_dim_asset_ibge_code", "dim_asset", ["ibge_code"])


def downgrade() -> None:
    op.drop_index("ix_dim_asset_ibge_code", table_name="dim_asset")
    op.drop_column("dim_asset", "ibge_code")
