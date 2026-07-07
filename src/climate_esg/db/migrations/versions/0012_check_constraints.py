"""check constraints de faixa: scores/coverage em [0,100], bandas e lat/long

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-06
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

log = logging.getLogger("alembic.runtime.migration")

_SCORE_TABLES = ("fact_physical_risk_score", "fact_transition_risk_score")

_CHECKS: list[tuple[str, str, str]] = [
    (
        "ck_dim_asset_latitude_range",
        "dim_asset",
        "latitude >= -90 AND latitude <= 90",
    ),
    (
        "ck_dim_asset_longitude_range",
        "dim_asset",
        "longitude >= -180 AND longitude <= 180",
    ),
    (
        "ck_fact_physical_risk_score_score_range",
        "fact_physical_risk_score",
        "score_0_100 >= 0 AND score_0_100 <= 100",
    ),
    (
        "ck_fact_physical_risk_score_coverage_range",
        "fact_physical_risk_score",
        "coverage_pct >= 0 AND coverage_pct <= 100",
    ),
    (
        "ck_fact_physical_risk_score_band",
        "fact_physical_risk_score",
        "band_low <= score_0_100 AND score_0_100 <= band_high",
    ),
    (
        "ck_fact_transition_risk_score_score_range",
        "fact_transition_risk_score",
        "score_0_100 >= 0 AND score_0_100 <= 100",
    ),
    (
        "ck_fact_transition_risk_score_band",
        "fact_transition_risk_score",
        "band_low <= score_0_100 AND score_0_100 <= band_high",
    ),
    (
        "ck_fact_financial_impact_band",
        "fact_financial_impact",
        "band_low_pct <= dcf_adjustment_pct AND dcf_adjustment_pct <= band_high_pct",
    ),
]


def _count(bind: sa.Connection, table: str, where: str) -> int:
    return bind.execute(sa.text(f"SELECT count(*) FROM {table} WHERE {where}")).scalar_one()


def upgrade() -> None:
    bind = op.get_bind()

    coords_where = "latitude < -90 OR latitude > 90 OR longitude < -180 OR longitude > 180"
    n = _count(bind, "dim_asset", coords_where)
    log.info("0012: dim_asset com coordenadas fora de faixa (anuladas): %d", n)
    if n:
        bind.execute(
            sa.text(
                f"UPDATE dim_asset SET latitude = NULL, longitude = NULL, geom = NULL "
                f"WHERE {coords_where}"
            )
        )

    for table in _SCORE_TABLES:
        score_where = "score_0_100 < 0 OR score_0_100 > 100"
        n = _count(bind, table, score_where)
        log.info("0012: %s com score fora de [0,100] (clamp): %d", table, n)
        if n:
            bind.execute(
                sa.text(
                    f"UPDATE {table} SET score_0_100 = LEAST(GREATEST(score_0_100, 0), 100) "
                    f"WHERE {score_where}"
                )
            )
        band_where = "band_low > score_0_100 OR band_high < score_0_100"
        n = _count(bind, table, band_where)
        log.info("0012: %s com banda inconsistente (expandida): %d", table, n)
        if n:
            bind.execute(
                sa.text(
                    f"UPDATE {table} SET band_low = LEAST(band_low, score_0_100), "
                    f"band_high = GREATEST(band_high, score_0_100) WHERE {band_where}"
                )
            )

    coverage_where = "coverage_pct < 0 OR coverage_pct > 100"
    n = _count(bind, "fact_physical_risk_score", coverage_where)
    log.info("0012: fact_physical_risk_score com coverage fora de [0,100] (clamp): %d", n)
    if n:
        bind.execute(
            sa.text(
                f"UPDATE fact_physical_risk_score "
                f"SET coverage_pct = LEAST(GREATEST(coverage_pct, 0), 100) "
                f"WHERE {coverage_where}"
            )
        )

    fin_band_where = "band_low_pct > dcf_adjustment_pct OR band_high_pct < dcf_adjustment_pct"
    n = _count(bind, "fact_financial_impact", fin_band_where)
    log.info("0012: fact_financial_impact com banda inconsistente (expandida): %d", n)
    if n:
        bind.execute(
            sa.text(
                f"UPDATE fact_financial_impact "
                f"SET band_low_pct = LEAST(band_low_pct, dcf_adjustment_pct), "
                f"band_high_pct = GREATEST(band_high_pct, dcf_adjustment_pct) "
                f"WHERE {fin_band_where}"
            )
        )

    for name, table, condition in _CHECKS:
        op.create_check_constraint(name, table, sa.text(condition))


def downgrade() -> None:
    for name, table, _condition in reversed(_CHECKS):
        op.drop_constraint(name, table, type_="check")
