from __future__ import annotations

import datetime as dt
import re
from dataclasses import asdict, dataclass, field
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from climate_esg.db.models import CacheDossier, CompanyFinancials, CvmFinancials, DimCompany
from climate_esg.ingestion.adaptabrasil import municipality_risk
from climate_esg.ingestion.cvm import normalize_name
from climate_esg.ingestion.geocoding import (
    BRASILAPI_CNPJ_URL,
    build_address_query,
    geocode,
    only_digits,
)
from climate_esg.ingestion.http import get_client
from climate_esg.ingestion.ibge import resolve_ibge_code
from climate_esg.ingestion.market_data import MarketData, fetch_market_data, resolve_ticker
from climate_esg.ingestion.news_collector import Article, controversy_ratio, fetch_news
from climate_esg.modeling.analytics import analyze_company

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
    company_sk: int | None = None
    ibge_code: str | None = None
    climate_risk: dict[str, Any] = field(default_factory=dict)
    climate_meta: dict[str, Any] = field(default_factory=dict)
    financials: dict[str, Any] | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_label: str | None = None
    cross: dict[str, Any] = field(default_factory=dict)
    predictions: dict[str, Any] = field(default_factory=dict)


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
        "cnae_codigo": p.get("cnae_fiscal"),
        "situacao": p.get("descricao_situacao_cadastral"),
        "porte": p.get("porte"),
        "natureza_juridica": p.get("natureza_juridica"),
        "capital_social": p.get("capital_social"),
        "data_inicio_atividade": p.get("data_inicio_atividade"),
        "logradouro": p.get("logradouro"),
        "numero": p.get("numero"),
        "complemento": p.get("complemento"),
        "bairro": p.get("bairro"),
        "cep": p.get("cep"),
        "uf": p.get("uf"),
        "municipio": p.get("municipio"),
        "telefone": p.get("ddd_telefone_1"),
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

    _attach_climate_risk(dossier)
    _attach_market_live(dossier)
    _attach_location(dossier)

    if dossier.name is None:
        dossier.name = query
    return dossier


def _attach_market_live(dossier: Dossier) -> None:
    if dossier.market is not None or not dossier.name:
        return
    try:
        ticker = resolve_ticker(dossier.name)
        if not ticker:
            return
        market = fetch_market_data(ticker)
        if market is not None:
            dossier.market = _market_dict(market)
            if "brapi" not in dossier.sources:
                dossier.sources.append("brapi")
    except Exception as exc:
        dossier.errors.append(f"brapi: {exc}")


def _attach_location(dossier: Dossier) -> None:
    if not dossier.registry:
        return
    reg = dossier.registry
    municipio = reg.get("municipio")
    uf = reg.get("uf")
    street_parts = [str(reg.get(k)) for k in ("logradouro", "numero") if reg.get(k)]
    street = " ".join(street_parts) or None
    try:
        result = None
        if street and municipio:
            result = geocode(
                build_address_query(street=street, municipality=str(municipio), state=str(uf or ""))
            )
        if result is None and municipio:
            result = geocode(
                build_address_query(municipality=str(municipio), state=str(uf or ""))
            )
        if result is not None:
            dossier.latitude = result.latitude
            dossier.longitude = result.longitude
            dossier.location_label = result.display_name
    except Exception as exc:
        dossier.errors.append(f"nominatim: {exc}")


def _attach_financials(session: Session, dossier: Dossier, cnpj: str | None) -> None:
    rec: CvmFinancials | None = None
    if cnpj:
        rec = session.scalar(
            sa.select(CvmFinancials)
            .where(CvmFinancials.cnpj == cnpj)
            .order_by(CvmFinancials.fiscal_year.desc())
            .limit(1)
        )
    if rec is None and dossier.name:
        rec = session.scalar(
            sa.select(CvmFinancials)
            .where(CvmFinancials.denom_norm == normalize_name(dossier.name))
            .order_by(CvmFinancials.fiscal_year.desc())
            .limit(1)
        )
    if rec is None:
        return
    revenue = float(rec.revenue) if rec.revenue is not None else None
    net_income = float(rec.net_income) if rec.net_income is not None else None
    ebit = float(rec.ebit) if rec.ebit is not None else None
    ebitda = float(rec.ebitda) if rec.ebitda is not None else None
    dossier.financials = {
        "cnpj": rec.cnpj,
        "revenue": revenue,
        "net_income": net_income,
        "ebit": ebit,
        "ebitda": ebitda,
        "net_margin": (net_income / revenue) if (net_income is not None and revenue) else None,
        "ebitda_margin": (ebitda / revenue) if (ebitda is not None and revenue) else None,
        "fiscal_year": int(rec.fiscal_year),
        "source": rec.source,
    }
    if "cvm" not in dossier.sources:
        dossier.sources.append("cvm")


def _attach_climate_risk(dossier: Dossier) -> None:
    if not dossier.registry:
        return
    municipio = dossier.registry.get("municipio")
    uf = dossier.registry.get("uf")
    if not (municipio and uf):
        return
    try:
        ibge = resolve_ibge_code(str(municipio), str(uf))
        if ibge:
            dossier.ibge_code = ibge
            dossier.climate_risk = municipality_risk(ibge)
            if dossier.climate_risk:
                dossier.climate_meta = {
                    "source": "AdaptaBrasil / MCTI",
                    "scenario": "SSP5-8.5",
                    "horizon": 2050,
                    "municipio": str(municipio),
                    "uf": str(uf),
                    "ibge": ibge,
                    "scale": "0–100 (índice de ameaça municipal)",
                }
                if "adaptabrasil" not in dossier.sources:
                    dossier.sources.append("adaptabrasil")
    except Exception as exc:
        dossier.errors.append(f"adaptabrasil: {exc}")


def normalize_key(query: str) -> str:
    s = query.strip()
    digits = only_digits(s)
    if len(digits) == 14:
        return f"cnpj:{digits}"
    if _TICKER_RE.match(s.upper()):
        return f"ticker:{s.upper()}"
    return "name:" + re.sub(r"\s+", "-", s.lower())


def _resolve_company_sk(session: Session, query: str, dossier: Dossier) -> int | None:
    if dossier.kind == "ticker":
        sk = session.scalar(
            sa.select(DimCompany.company_sk).where(DimCompany.ticker == query.strip().upper())
        )
        if sk is not None:
            return int(sk)

    if dossier.kind == "cnpj":
        sk = session.scalar(
            sa.select(CompanyFinancials.company_sk).where(
                CompanyFinancials.cnpj == only_digits(query)
            )
        )
        if sk is not None:
            return int(sk)

    if dossier.name:
        name = dossier.name.strip()
        sk = session.scalar(
            sa.select(DimCompany.company_sk).where(DimCompany.name.ilike(name))
        )
        if sk is not None:
            return int(sk)
        core = re.sub(r"\s+s\.?\s*a\.?$", "", name, flags=re.IGNORECASE).strip()
        if len(core) >= 3:
            sk = session.scalar(
                sa.select(DimCompany.company_sk)
                .where(DimCompany.name.ilike(f"%{core}%"))
                .order_by(DimCompany.company_sk)
                .limit(1)
            )
            if sk is not None:
                return int(sk)
    return None


def _consolidate_internal(session: Session, dossier: Dossier) -> None:
    company = session.get(DimCompany, dossier.company_sk)
    if company is None:
        return
    if dossier.name is None:
        dossier.name = company.name

    if company.ticker and dossier.market is None:
        try:
            market = fetch_market_data(company.ticker)
            if market is not None:
                dossier.market = _market_dict(market)
                if "brapi" not in dossier.sources:
                    dossier.sources.append("brapi")
        except Exception as exc:
            dossier.errors.append(f"brapi: {exc}")

    fin = session.execute(
        sa.select(
            CompanyFinancials.revenue,
            CompanyFinancials.net_income,
            CompanyFinancials.fiscal_year,
            CompanyFinancials.cnpj,
        )
        .where(CompanyFinancials.company_sk == dossier.company_sk)
        .order_by(CompanyFinancials.fiscal_year.desc())
        .limit(1)
    ).first()

    cnpj = None
    if fin is not None:
        revenue, net_income, fiscal_year, cnpj = fin
        dossier.financials = {
            "revenue": float(revenue) if revenue is not None else None,
            "net_income": float(net_income) if net_income is not None else None,
            "fiscal_year": int(fiscal_year),
        }
        if "cvm" not in dossier.sources:
            dossier.sources.append("cvm")

    if dossier.registry is None and cnpj:
        try:
            reg = _registry(str(cnpj))
            if reg:
                dossier.registry = reg
                dossier.name = dossier.name or reg.get("nome_fantasia") or reg.get("razao_social")
                if "brasilapi" not in dossier.sources:
                    dossier.sources.append("brasilapi")
                _attach_climate_risk(dossier)
        except Exception as exc:
            dossier.errors.append(f"brasilapi: {exc}")


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
    dossier.company_sk = _resolve_company_sk(session, query, dossier)
    if dossier.company_sk is not None:
        _consolidate_internal(session, dossier)
    _attach_financials(
        session, dossier, only_digits(query) if dossier.kind == "cnpj" else None
    )

    fin_cnpj = (dossier.financials or {}).get("cnpj")
    analytics_cnpj = fin_cnpj or (only_digits(query) if dossier.kind == "cnpj" else None)
    try:
        result = analyze_company(
            session,
            analytics_cnpj,
            name=dossier.name or query,
            climate_risk=dossier.climate_risk,
            revenue=(dossier.financials or {}).get("revenue"),
        )
        dossier.cross = result.get("cross", {})
        dossier.predictions = result.get("predictions", {})
    except Exception as exc:
        dossier.errors.append(f"analytics: {exc}")

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
