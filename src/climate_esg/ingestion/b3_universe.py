from __future__ import annotations

import datetime as dt
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from climate_esg.config import get_settings
from climate_esg.db.models import DimCompany
from climate_esg.ingestion.http import get_client

BRAPI_LIST_URL = "https://brapi.dev/api/quote/list"
_VALIDITY_FROM = dt.date(2026, 1, 1)


def fetch_b3_list(target: int = 200, *, token: str | None = None) -> list[dict[str, Any]]:
    tok = token if token is not None else get_settings().brapi_token.get_secret_value()
    stocks: list[dict[str, Any]] = []
    page = 1
    while len(stocks) < target:
        params: dict[str, str | int] = {
            "limit": min(target, 200),
            "page": page,
            "type": "stock",
        }
        if tok:
            params["token"] = tok
        resp = get_client().get(BRAPI_LIST_URL, params=params, timeout=30.0)
        resp.raise_for_status()
        payload = resp.json()
        batch = payload.get("stocks") or []
        if not batch:
            break
        stocks.extend(batch)
        if not payload.get("hasNextPage"):
            break
        page += 1
    return stocks[:target]


def ingest_b3_universe(session: Session, target: int = 200) -> int:
    stocks = fetch_b3_list(target)
    existing = set(
        session.scalars(sa.select(DimCompany.ticker).where(DimCompany.ticker.is_not(None))).all()
    )
    max_sk = session.scalar(sa.select(sa.func.max(DimCompany.company_sk))) or 0
    added = 0
    for s in stocks:
        ticker = s.get("stock")
        if not ticker:
            continue
        market_cap = s.get("market_cap")
        if ticker in existing:
            if market_cap is not None:
                session.execute(
                    sa.update(DimCompany)
                    .where(DimCompany.ticker == ticker)
                    .values(market_cap=market_cap)
                )
            continue
        max_sk += 1
        session.add(
            DimCompany(
                company_sk=max_sk,
                ticker=ticker,
                name=(s.get("name") or ticker)[:255],
                subsector=(s.get("sector") or None) and str(s.get("sector"))[:50],
                country="BR",
                is_listed=True,
                market_cap=market_cap,
                validity_from=_VALIDITY_FROM,
            )
        )
        existing.add(ticker)
        added += 1
    return added
