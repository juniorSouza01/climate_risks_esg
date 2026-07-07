from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, NamedTuple

import httpx

from climate_esg.config import get_settings
from climate_esg.ingestion.http import request_json
from climate_esg.logging import get_logger
from climate_esg.quality.boundaries import validate_brapi_quote

log = get_logger(__name__)

BRAPI_QUOTE_URL = "https://brapi.dev/api/quote/{ticker}"
BRAPI_LIST_URL = "https://brapi.dev/api/quote/list"

_TICKER_RE = re.compile(r"^[A-Z]{4}(\d{1,2})$")
_SUFFIX_PRIORITY = {"3": 0, "4": 1, "11": 2}


class BrapiAuthError(RuntimeError):
    pass


class TickerResolution(NamedTuple):
    ticker: str
    confidence: str


def _brapi_search(query: str, tok: str | None, timeout: float | None) -> list[dict[str, Any]]:
    params: dict[str, str] = {"search": query}
    if tok:
        params["token"] = tok
    try:
        payload = request_json("brapi", BRAPI_LIST_URL, params=params, timeout=timeout)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (401, 402, 404):
            return []
        raise
    return [s for s in ((payload or {}).get("stocks") or []) if s.get("stock")]


def _suffix_rank(ticker: str) -> int:
    m = _TICKER_RE.match(ticker)
    if not m:
        return 9
    return _SUFFIX_PRIORITY.get(m.group(1), 3)


def _select_candidate(candidates: list[dict[str, Any]]) -> TickerResolution | None:
    if not candidates:
        return None
    valid = [c for c in candidates if _TICKER_RE.match(str(c["stock"]))]
    pool = valid or candidates
    best = sorted(
        pool,
        key=lambda c: (
            _suffix_rank(str(c["stock"])),
            -float(c.get("volume") or 0.0),
            str(c["stock"]),
        ),
    )[0]
    confidence = "exact" if len(valid) == 1 else "heuristic"
    return TickerResolution(ticker=str(best["stock"]), confidence=confidence)


def resolve_ticker_info(
    name: str, *, token: str | None = None, timeout: float | None = None
) -> TickerResolution | None:
    if not name or len(name.strip()) < 3:
        return None
    tok = token if token is not None else get_settings().brapi_token.get_secret_value()
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
        resolution = _select_candidate(_brapi_search(q, tok, timeout))
        if resolution is not None:
            return resolution
    return None


def resolve_ticker(
    name: str, *, token: str | None = None, timeout: float | None = None
) -> str | None:
    resolution = resolve_ticker_info(name, token=token, timeout=timeout)
    return resolution.ticker if resolution else None


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
    closing_prices: list[float] = field(default_factory=list)


def compute_daily_returns(closes: list[float]) -> list[float]:
    return [
        (closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes)) if closes[i - 1]
    ]


def annualized_volatility(closes: list[float]) -> float | None:
    if len(closes) < 3:
        return None
    rets = compute_daily_returns(closes)
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
        daily_returns=compute_daily_returns(closes),
        closing_prices=closes,
    )


def _handle_brapi_status(ticker: str, exc: httpx.HTTPStatusError) -> None:
    status = exc.response.status_code
    if status in (401, 402):
        log.error("brapi.auth_failed", ticker=ticker, status_code=status)
        raise BrapiAuthError(
            f"brapi: token ausente/expirado (HTTP {status}) para {ticker}"
        ) from exc
    if status == 404:
        log.info("brapi.ticker_not_found", ticker=ticker, status_code=status)
        return
    raise exc


def fetch_market_data(
    ticker: str, *, token: str | None = None, timeout: float | None = None
) -> MarketData | None:
    tok = token if token is not None else get_settings().brapi_token.get_secret_value()
    base: dict[str, str] = {"token": tok} if tok else {}
    url = BRAPI_QUOTE_URL.format(ticker=ticker)

    # Histórico (range/interval) dá a volatilidade, mas exige plano pago na brapi.
    # Se o plano recusar (400/402/422), cai para o quote básico (preço/market cap/P-L).
    try:
        payload = request_json(
            "brapi", url, params={**base, "range": "1y", "interval": "1d"}, timeout=timeout
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code not in (400, 402, 422):
            _handle_brapi_status(ticker, exc)
            return None
        try:
            payload = request_json("brapi", url, params=base, timeout=timeout)
        except httpx.HTTPStatusError as exc2:
            _handle_brapi_status(ticker, exc2)
            return None
    if payload is None:
        return None
    market = parse_brapi_quote(payload)
    if market is not None:
        validate_brapi_quote(market.ticker, market.price, market.market_cap)
    return market
