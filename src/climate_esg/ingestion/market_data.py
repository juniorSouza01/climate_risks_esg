from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from climate_esg.config import get_settings
from climate_esg.ingestion.http import get_client

BRAPI_QUOTE_URL = "https://brapi.dev/api/quote/{ticker}"


@dataclass(frozen=True, slots=True)
class MarketData:
    ticker: str
    name: str | None
    currency: str | None
    price: float | None
    market_cap: float | None
    pe_ratio: float | None
    annualized_volatility: float | None
    daily_returns: list[float] = field(default_factory=list)


def annualized_volatility(closes: list[float]) -> float | None:
    if len(closes) < 3:
        return None
    rets = [
        (closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes)) if closes[i - 1]
    ]
    if len(rets) < 2:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var) * math.sqrt(252)


def parse_brapi_quote(payload: dict[str, Any]) -> MarketData | None:
    results = payload.get("results") or []
    if not results:
        return None
    r = results[0]
    history = r.get("historicalDataPrice") or []
    closes = [h["close"] for h in history if h.get("close") is not None]
    return MarketData(
        ticker=str(r.get("symbol", "")),
        name=r.get("longName") or r.get("shortName"),
        currency=r.get("currency"),
        price=r.get("regularMarketPrice"),
        market_cap=r.get("marketCap"),
        pe_ratio=r.get("priceEarnings"),
        annualized_volatility=annualized_volatility(closes),
        daily_returns=closes,
    )


def fetch_market_data(
    ticker: str, *, token: str | None = None, timeout: float = 20.0
) -> MarketData | None:
    params: dict[str, str] = {"range": "1y", "interval": "1d"}
    tok = token if token is not None else get_settings().brapi_token
    if tok:
        params["token"] = tok
    resp = get_client().get(BRAPI_QUOTE_URL.format(ticker=ticker), params=params, timeout=timeout)
    if resp.status_code in (401, 402, 404):
        return None
    resp.raise_for_status()
    return parse_brapi_quote(resp.json())
