from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

from climate_esg.config import get_settings
from climate_esg.ingestion.http import get_client

BRAPI_QUOTE_URL = "https://brapi.dev/api/quote/{ticker}"
BRAPI_LIST_URL = "https://brapi.dev/api/quote/list"

_TICKER_RE = re.compile(r"^[A-Z]{4}\d{1,2}$")


def _brapi_search(query: str, tok: str | None, timeout: float) -> list[str]:
    params: dict[str, str] = {"search": query}
    if tok:
        params["token"] = tok
    resp = get_client().get(BRAPI_LIST_URL, params=params, timeout=timeout)
    if resp.status_code in (401, 402, 404):
        return []
    resp.raise_for_status()
    return [str(s.get("stock")) for s in (resp.json().get("stocks") or []) if s.get("stock")]


def resolve_ticker(name: str, *, token: str | None = None, timeout: float = 20.0) -> str | None:
    if not name or len(name.strip()) < 3:
        return None
    tok = token if token is not None else get_settings().brapi_token
    tokens = name.strip().split()
    queries = [name.strip()]
    if len(tokens) >= 2:
        queries.append(" ".join(tokens[:2]))
    queries.append(tokens[0])
    seen: set[str] = set()
    for q in queries:
        if len(q) < 3 or q in seen:
            continue
        seen.add(q)
        candidates = _brapi_search(q, tok, timeout)
        exact = [c for c in candidates if _TICKER_RE.match(c)]
        if exact:
            return sorted(exact, key=len)[0]
        if candidates:
            return candidates[0]
    return None


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
    tok = token if token is not None else get_settings().brapi_token
    base: dict[str, str] = {"token": tok} if tok else {}
    url = BRAPI_QUOTE_URL.format(ticker=ticker)

    # Histórico (range/interval) dá a volatilidade, mas exige plano pago na brapi.
    # Se o plano recusar (400/402/422), cai para o quote básico (preço/market cap/P-L).
    resp = get_client().get(url, params={**base, "range": "1y", "interval": "1d"}, timeout=timeout)
    if resp.status_code in (400, 402, 422):
        resp = get_client().get(url, params=base, timeout=timeout)
    if resp.status_code in (401, 402, 404):
        return None
    resp.raise_for_status()
    return parse_brapi_quote(resp.json())
