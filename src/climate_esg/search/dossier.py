from __future__ import annotations

import datetime as dt
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from climate_esg.db.models import CacheDossier
from climate_esg.ingestion.geocoding import BRASILAPI_CNPJ_URL, only_digits
from climate_esg.ingestion.http import get_client
from climate_esg.ingestion.market_data import MarketData, fetch_market_data
from climate_esg.ingestion.news_collector import Article, controversy_ratio, fetch_news

_TICKER_RE = re.compile(r"^[A-Z]{4}\d{1,2}$")


@dataclass
class Dossier:
    query: str
    kind: str
    name: str | None = None
    registry: dict[str, Any] | None = None
    market: dict[str, Any] | None = None
    news: list[dict[str, Any]] = field(default_factory=list)
    controversy_ratio: float = 0.0
    sources: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    fetched_at: str | None = None
    cached: bool = False


def classify_query(query: str) -> str:
    s = query.strip()
    if len(only_digits(s)) == 14 and only_digits(s) == s.replace(".", "").replace("/", "").replace(
        "-", ""
    ):
        return "cnpj"
    if _TICKER_RE.match(s.upper()):
        return "ticker"
    return "name"


def _registry(cnpj: str, *, timeout: float = 20.0) -> dict[str, Any] | None:
    resp = get_client().get(BRASILAPI_CNPJ_URL.format(cnpj=only_digits(cnpj)), timeout=timeout)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    p = resp.json()
    return {
        "razao_social": p.get("razao_social"),
        "nome_fantasia": p.get("nome_fantasia"),
        "cnae": p.get("cnae_fiscal_descricao"),
        "situacao": p.get("descricao_situacao_cadastral"),
        "porte": p.get("porte"),
        "capital_social": p.get("capital_social"),
        "uf": p.get("uf"),
        "municipio": p.get("municipio"),
        "socios": [s.get("nome_socio") for s in (p.get("qsa") or [])],
    }


def _market_dict(m: MarketData) -> dict[str, Any]:
    return {
        "ticker": m.ticker,
        "name": m.name,
        "currency": m.currency,
        "price": m.price,
        "market_cap": m.market_cap,
        "pe_ratio": m.pe_ratio,
        "annualized_volatility": m.annualized_volatility,
        "n_observations": len(m.daily_returns),
    }


def _article_dict(a: Article) -> dict[str, Any]:
    return {"title": a.title, "url": a.url, "domain": a.domain, "seendate": a.seendate}


def build_dossier(query: str, *, max_news: int = 25) -> Dossier:
    kind = classify_query(query)
    dossier = Dossier(query=query, kind=kind)

    if kind == "cnpj":
        try:
            reg = _registry(query)
            if reg is not None:
                dossier.registry = reg
                dossier.name = reg.get("nome_fantasia") or reg.get("razao_social")
                dossier.sources.append("brasilapi")
        except Exception as exc:
            dossier.errors.append(f"brasilapi: {exc}")

    if kind == "ticker":
        try:
            market = fetch_market_data(query.upper())
            if market is not None:
                dossier.market = _market_dict(market)
                dossier.name = market.name or dossier.name
                dossier.sources.append("brapi")
        except Exception as exc:
            dossier.errors.append(f"brapi: {exc}")

    name_for_news = dossier.name or query
    try:
        articles = fetch_news(name_for_news, max_records=max_news)
        if articles:
            dossier.news = [_article_dict(a) for a in articles[:max_news]]
            dossier.controversy_ratio = controversy_ratio(articles)
            dossier.sources.append("gdelt")
    except Exception as exc:
        dossier.errors.append(f"gdelt: {exc}")

    if dossier.name is None:
        dossier.name = query
    return dossier


def normalize_key(query: str) -> str:
    s = query.strip()
    digits = only_digits(s)
    if len(digits) == 14:
        return f"cnpj:{digits}"
    if _TICKER_RE.match(s.upper()):
        return f"ticker:{s.upper()}"
    return "name:" + re.sub(r"\s+", "-", s.lower())


def get_or_build_dossier(
    session: Session, query: str, *, ttl_s: int = 3600, max_news: int = 25
) -> dict[str, Any]:
    key = normalize_key(query)
    now = dt.datetime.now(dt.UTC)

    row = session.get(CacheDossier, key)
    if row is not None and row.expires_at > now:
        payload = dict(row.payload)
        payload["cached"] = True
        return payload

    dossier = build_dossier(query, max_news=max_news)
    dossier.fetched_at = now.isoformat()
    payload = asdict(dossier)
    session.merge(
        CacheDossier(
            query_key=key,
            kind=dossier.kind,
            payload=payload,
            expires_at=now + dt.timedelta(seconds=ttl_s),
        )
    )
    session.commit()
    payload["cached"] = False
    return payload
