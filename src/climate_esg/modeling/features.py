from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import sqlalchemy as sa
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sqlalchemy.orm import Session

from climate_esg.db.models import CompanyFinancials, DimCompany


@dataclass
class CompanyFeatures:
    company_sks: list[int]
    names: list[str]
    matrix: Any


def _latest_financials(session: Session) -> dict[int, tuple[float | None, float | None]]:
    latest = (
        sa.select(
            CompanyFinancials.company_sk,
            sa.func.max(CompanyFinancials.fiscal_year).label("fy"),
        )
        .group_by(CompanyFinancials.company_sk)
        .subquery()
    )
    rows = session.execute(
        sa.select(
            CompanyFinancials.company_sk,
            CompanyFinancials.revenue,
            CompanyFinancials.net_income,
        ).join(
            latest,
            sa.and_(
                CompanyFinancials.company_sk == latest.c.company_sk,
                CompanyFinancials.fiscal_year == latest.c.fy,
            ),
        )
    ).all()
    return {int(sk): (rev, ni) for sk, rev, ni in rows}


def _impute_log(values: list[float]) -> Any:
    arr = np.array(values, dtype=float)
    median = np.nanmedian(arr)
    if not np.isfinite(median):
        median = 0.0
    arr = np.where(np.isnan(arr), median, arr)
    return np.log1p(np.maximum(arr, 0.0)).reshape(-1, 1)


def build_company_features(session: Session) -> CompanyFeatures:
    rows = session.execute(
        sa.select(
            DimCompany.company_sk,
            DimCompany.name,
            DimCompany.subsector,
            DimCompany.market_cap,
        ).order_by(DimCompany.company_sk)
    ).all()
    if not rows:
        return CompanyFeatures([], [], np.empty((0, 0)))

    fin = _latest_financials(session)
    company_sks = [int(r[0]) for r in rows]
    names = [str(r[1]) for r in rows]
    sectors = [[str(r[2] or "UNKNOWN")] for r in rows]
    mcaps = [float(r[3]) if r[3] is not None else np.nan for r in rows]

    revenues: list[float] = []
    margins: list[float] = []
    for sk in company_sks:
        rev, ni = fin.get(sk, (None, None))
        revenues.append(float(rev) if rev is not None else float("nan"))
        if rev is not None and ni is not None and float(rev) != 0.0:
            margins.append(float(ni) / float(rev))
        else:
            margins.append(float("nan"))
    margin_arr = np.array(margins, dtype=float)
    margin_med = np.nanmedian(margin_arr)
    margin_arr = np.where(
        np.isnan(margin_arr), margin_med if np.isfinite(margin_med) else 0.0, margin_arr
    ).reshape(-1, 1)

    numeric = StandardScaler().fit_transform(
        np.hstack([_impute_log(mcaps), _impute_log(revenues), margin_arr])
    )
    categorical = OneHotEncoder(handle_unknown="ignore", sparse_output=False).fit_transform(sectors)
    matrix = np.hstack([numeric, categorical])
    return CompanyFeatures(company_sks=company_sks, names=names, matrix=matrix)
