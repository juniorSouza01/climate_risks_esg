from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import sqlalchemy as sa
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sqlalchemy.orm import Session

from climate_esg.db.models import DimCompany


@dataclass
class CompanyFeatures:
    company_sks: list[int]
    names: list[str]
    matrix: Any


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

    company_sks = [int(r[0]) for r in rows]
    names = [str(r[1]) for r in rows]
    sectors = [[str(r[2] or "UNKNOWN")] for r in rows]
    mcaps = np.array([float(r[3]) if r[3] is not None else np.nan for r in rows], dtype=float)

    median = np.nanmedian(mcaps)
    if not np.isfinite(median):
        median = 0.0
    mcaps = np.where(np.isnan(mcaps), median, mcaps)
    log_mcap = np.log1p(np.maximum(mcaps, 0.0)).reshape(-1, 1)

    numeric = StandardScaler().fit_transform(log_mcap)
    categorical = OneHotEncoder(handle_unknown="ignore", sparse_output=False).fit_transform(sectors)
    matrix = np.hstack([numeric, categorical])
    return CompanyFeatures(company_sks=company_sks, names=names, matrix=matrix)
