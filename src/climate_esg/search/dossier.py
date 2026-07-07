from __future__ import annotations

import datetime as dt
import re
from dataclasses import asdict, dataclass, field
from typing import Any

import httpx
import sqlalchemy as sa
from sqlalchemy.orm import Session

from climate_esg.config import get_settings
from climate_esg.db.models import CacheDossier, CompanyFinancials, CvmFinancials, DimCompany
from climate_esg.ingestion.adaptabrasil import municipality_risk
from climate_esg.ingestion.cnae_value_chain import value_chain
from climate_esg.ingestion.cvm import normalize_name
from climate_esg.ingestion.geocoding import (
    BRASILAPI_CNPJ_URL,
    build_address_query,
    geocode,
    only_digits,
)
from climate_esg.ingestion.http import get_client
from climate_esg.ingestion.ibge import resolve_ibge_code
from climate_esg.ingestion.market_data import (
    BrapiAuthError,
    MarketData,
    fetch_market_data,
    resolve_ticker_info,
)
from climate_esg.ingestion.news_collector import Article, controversy_ratio, fetch_news
from climate_esg.ingestion.procurement import fetch_gov_supplier
from climate_esg.logging import get_logger
from climate_esg.modeling.analytics import analyze_company
from climate_esg.modeling.climate_financial import climate_financial_impact
from climate_esg.modeling.supply_chain import supply_chain_climate_risk

log = get_logger(__name__)

_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9]{3}\d{1,2}$")
_CACHE_KEY_VERSION = "v2"
DEGRADED_TTL_S = 300

_CNPJ_WEIGHTS_1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_CNPJ_WEIGHTS_2 = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)


def _cnpj_check_digit(digits: str, weights: tuple[int, ...]) -> int:
    total = sum(int(d) * w for d, w in zip(digits, weights, strict=True))
    rest = total % 11
    return 0 if rest < 2 else 11 - rest


def valid_cnpj(digits: str) -> bool:
    if len(digits) != 14 or not digits.isdigit() or len(set(digits)) == 1:
        return False
    if int(digits[12]) != _cnpj_check_digit(digits[:12], _CNPJ_WEIGHTS_1):
        return False
    return int(digits[13]) == _cnpj_check_digit(digits[:13], _CNPJ_WEIGHTS_2)


def _default_news() -> dict[str, Any]:
    return {"status": "ok", "reason": None, "articles": []}


@dataclass
class Dossier:
    query: str
    kind: str
    name: str | None = None
    registry: dict[str, Any] | None = None
    market: dict[str, Any] | None = None
    news: dict[str, Any] = field(default_factory=_default_news)
    controversy_ratio: float | None = None
    sources: list[str] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
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
    climate_financial: dict[str, Any] = field(default_factory=dict)
    relationships: dict[str, Any] | None = None
    supply_chain: dict[str, Any] = field(default_factory=dict)


def _classify_exception(exc: Exception) -> tuple[str, bool]:
    if isinstance(exc, BrapiAuthError):
        return "auth", False
    if isinstance(exc, httpx.TimeoutException):
        return "timeout", True
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return f"http_{status}", status == 429 or status >= 500
    if isinstance(exc, httpx.HTTPError):
        return "network", True
    if isinstance(exc, ValueError):
        return "invalid_input", False
    return "unexpected", False


def _record_error(dossier: Dossier, source: str, exc: Exception) -> None:
    code, transient = _classify_exception(exc)
    log.warning("dossier.section_failed", source=source, code=code, error=str(exc))
    dossier.errors.append({"source": source, "code": code, "transient": transient})


def classify_query(query: str) -> str:
    s = query.strip()
    digits = only_digits(s)
    if (
        len(digits) == 14
        and digits == s.replace(".", "").replace("/", "").replace("-", "")
        and valid_cnpj(digits)
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
        "cnpj": only_digits(str(p.get("cnpj") or cnpj)),
        "razao_social": p.get("razao_social"),
        "nome_fantasia": p.get("nome_fantasia"),
        "cnae": p.get("cnae_fiscal_descricao"),
        "cnae_codigo": p.get("cnae_fiscal"),
        "cnaes_secundarios": [
            {"codigo": c.get("codigo"), "descricao": c.get("descricao")}
            for c in (p.get("cnaes_secundarios") or [])
            if c.get("codigo")
        ],
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
        "socios": [s.get("nome_socio") for s in (p.get("qsa") or []) if s.get("nome_socio")],
    }


def _market_dict(m: MarketData, *, confidence: str | None = None) -> dict[str, Any]:
    return {
        "status": "ok",
        "reason": None,
        "ticker": m.ticker,
        "name": m.name,
        "currency": m.currency,
        "price": m.price,
        "market_cap": m.market_cap,
        "pe_ratio": m.pe_ratio,
        "annualized_volatility": m.annualized_volatility,
        "n_observations": len(m.closing_prices),
        "confidence": confidence,
    }


def _article_dict(a: Article) -> dict[str, Any]:
    return {"title": a.title, "url": a.url, "domain": a.domain, "seendate": a.seendate}


def _names_match(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return False
    if na in nb or nb in na:
        return True
    ta, tb = set(na.split()), set(nb.split())
    common = ta & tb
    if not common:
        return False
    return len(common) / min(len(ta), len(tb)) >= 0.5


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
            _record_error(dossier, "brasilapi", exc)

    if kind == "ticker":
        try:
            market = fetch_market_data(query.upper())
            if market is not None:
                dossier.market = _market_dict(market, confidence="exact")
                dossier.name = market.name or dossier.name
                dossier.sources.append("brapi")
        except Exception as exc:
            _record_error(dossier, "brapi", exc)

    _attach_news(dossier, max_news=max_news)
    _attach_climate_risk(dossier)
    _attach_market_live(dossier)
    _attach_location(dossier)

    if dossier.name is None:
        dossier.name = query
    return dossier


def _attach_news(dossier: Dossier, *, max_news: int) -> None:
    name_for_news = dossier.name or dossier.query
    articles: list[Article] | None = None
    try:
        articles = fetch_news(name_for_news, max_records=max_news)
    except Exception as exc:
        _record_error(dossier, "gdelt", exc)
    if articles is None:
        dossier.news = {
            "status": "error",
            "reason": "coleta de notícias indisponível (GDELT fora do ar ou em rate-limit)",
            "articles": [],
        }
        dossier.controversy_ratio = None
        if not any(e.get("source") == "gdelt" for e in dossier.errors):
            dossier.errors.append({"source": "gdelt", "code": "unavailable", "transient": True})
        return
    dossier.news = {
        "status": "ok",
        "reason": None,
        "articles": [_article_dict(a) for a in articles[:max_news]],
    }
    dossier.controversy_ratio = controversy_ratio(articles)
    if "gdelt" not in dossier.sources:
        dossier.sources.append("gdelt")


def _attach_market_live(dossier: Dossier) -> None:
    if dossier.market is not None or not dossier.name:
        return
    try:
        resolution = resolve_ticker_info(dossier.name)
        if resolution is None:
            return
        market = fetch_market_data(resolution.ticker)
        if market is None:
            return
        reg = dossier.registry or {}
        candidates = [dossier.name, reg.get("razao_social"), reg.get("nome_fantasia")]
        matched = any(_names_match(c, market.name) for c in candidates if c)
        if not matched:
            dossier.market = {
                "status": "unresolved",
                "reason": (
                    f"ticker {resolution.ticker} (associação {resolution.confidence}) "
                    "não confere com o nome/CNPJ da empresa — dados de mercado omitidos"
                ),
            }
            return
        dossier.market = _market_dict(market, confidence=resolution.confidence)
        if "brapi" not in dossier.sources:
            dossier.sources.append("brapi")
    except Exception as exc:
        _record_error(dossier, "brapi", exc)


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
        _record_error(dossier, "nominatim", exc)


def _attach_financials(session: Session, dossier: Dossier, cnpj: str | None) -> None:
    rows: list[CvmFinancials] = []
    if cnpj:
        rows = list(
            session.scalars(
                sa.select(CvmFinancials)
                .where(CvmFinancials.cnpj == cnpj)
                .order_by(CvmFinancials.fiscal_year.desc())
            )
        )
    if not rows and dossier.name:
        rows = list(
            session.scalars(
                sa.select(CvmFinancials)
                .where(CvmFinancials.denom_norm == normalize_name(dossier.name))
                .order_by(CvmFinancials.fiscal_year.desc())
            )
        )
    if not rows:
        return

    def _f(v: Any) -> float | None:
        return float(v) if v is not None else None

    rec = rows[0]
    revenue = _f(rec.revenue)
    net_income = _f(rec.net_income)
    ebit = _f(rec.ebit)
    ebitda = _f(rec.ebitda)
    total_assets = _f(rec.total_assets)
    equity = _f(rec.equity)
    gross_debt = _f(rec.gross_debt)

    history = [
        {
            "fiscal_year": int(r.fiscal_year),
            "revenue": _f(r.revenue),
            "ebitda": _f(r.ebitda),
            "net_income": _f(r.net_income),
        }
        for r in rows
    ]
    prev_revenue = next(
        (h["revenue"] for h in history[1:] if h["revenue"]), None
    )
    revenue_growth = (
        (revenue - prev_revenue) / prev_revenue
        if (revenue is not None and prev_revenue)
        else None
    )

    dossier.financials = {
        "cnpj": rec.cnpj,
        "revenue": revenue,
        "net_income": net_income,
        "ebit": ebit,
        "ebitda": ebitda,
        "total_assets": total_assets,
        "equity": equity,
        "gross_debt": gross_debt,
        "net_margin": (net_income / revenue) if (net_income is not None and revenue) else None,
        "ebitda_margin": (ebitda / revenue) if (ebitda is not None and revenue) else None,
        "debt_to_ebitda": (gross_debt / ebitda) if (gross_debt is not None and ebitda) else None,
        "roe": (net_income / equity) if (net_income is not None and equity) else None,
        "revenue_growth": revenue_growth,
        "history": history,
        "fiscal_year": int(rec.fiscal_year),
        "source": rec.source,
    }
    if "cvm" not in dossier.sources:
        dossier.sources.append("cvm")


def _attach_relationships(dossier: Dossier, cnpj: str | None) -> None:
    if not cnpj:
        return
    reg = dossier.registry or {}
    rel: dict[str, Any] = {"cnpj": cnpj}

    try:
        gov = fetch_gov_supplier(cnpj)
        rel["gov_supplier"] = gov
        if gov and gov.get("found") and "compras.gov.br" not in dossier.sources:
            dossier.sources.append("compras.gov.br")
    except Exception as exc:
        _record_error(dossier, "compras_gov", exc)
        rel["gov_supplier"] = None

    socios = reg.get("socios") or []
    rel["socios"] = (
        {"items": socios, "count": len(socios), "seal": "factual", "source": "brasilapi/qsa"}
        if socios
        else None
    )
    rel["value_chain"] = value_chain(reg.get("cnae_codigo"))
    rel["public_contracts"] = {
        "available": bool(get_settings().portal_transparencia_token),
        "reason": "requer PORTAL_TRANSPARENCIA_TOKEN (Portal da Transparência)",
        "seal": "previsto",
        "source": "portaldatransparencia",
    }
    dossier.relationships = rel


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
                    "scale": "0–1 (índice de ameaça municipal normalizado)",
                }
                if "adaptabrasil" not in dossier.sources:
                    dossier.sources.append("adaptabrasil")
    except Exception as exc:
        _record_error(dossier, "adaptabrasil", exc)


def normalize_key(query: str) -> str:
    s = query.strip()
    digits = only_digits(s)
    if len(digits) == 14 and valid_cnpj(digits):
        return f"{_CACHE_KEY_VERSION}:cnpj:{digits}"
    if _TICKER_RE.match(s.upper()):
        return f"{_CACHE_KEY_VERSION}:ticker:{s.upper()}"
    return f"{_CACHE_KEY_VERSION}:name:" + re.sub(r"\s+", "-", s.lower())


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


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
            sa.select(DimCompany.company_sk).where(
                DimCompany.name.ilike(_escape_like(name), escape="\\")
            )
        )
        if sk is not None:
            return int(sk)
        core = re.sub(r"\s+s\.?\s*a\.?$", "", name, flags=re.IGNORECASE).strip()
        if len(core) >= 3:
            sk = session.scalar(
                sa.select(DimCompany.company_sk)
                .where(DimCompany.name.ilike(f"%{_escape_like(core)}%", escape="\\"))
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
                dossier.market = _market_dict(market, confidence="exact")
                if "brapi" not in dossier.sources:
                    dossier.sources.append("brapi")
        except Exception as exc:
            _record_error(dossier, "brapi", exc)

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
            _record_error(dossier, "brasilapi", exc)


def _section_result(result: dict[str, Any]) -> dict[str, Any]:
    out = dict(result)
    out.setdefault("status", "ok")
    out.setdefault("reason", None)
    return out


def _attach_analytics(session: Session, dossier: Dossier, analytics_cnpj: str | None) -> None:
    try:
        result = analyze_company(
            session,
            analytics_cnpj,
            name=dossier.name or dossier.query,
            climate_risk=dossier.climate_risk,
            revenue=(dossier.financials or {}).get("revenue"),
        )
        status = result.get("status", "ok")
        reason = result.get("reason")
        cross = dict(result.get("cross") or {})
        cross["status"] = status
        cross["reason"] = reason
        dossier.cross = cross
        predictions = dict(result.get("predictions") or {})
        if status == "ok" and not predictions:
            predictions = {
                "status": "no_input",
                "reason": "empresa fora do universo CVM (sem CNPJ casado) — ML indisponível",
            }
        else:
            predictions["status"] = status
            predictions["reason"] = reason
        dossier.predictions = predictions
    except Exception as exc:
        _record_error(dossier, "analytics", exc)
        notice = {"status": "error", "reason": "falha interna na análise cruzada"}
        dossier.cross = dict(notice)
        dossier.predictions = dict(notice)


def _attach_climate_financial(dossier: Dossier) -> None:
    try:
        reg = dossier.registry or {}
        fin = dossier.financials or {}
        mkt = dossier.market if (dossier.market or {}).get("status") == "ok" else {}
        climate_index = (dossier.cross.get("climate_index") or {}).get("value")
        dossier.climate_financial = _section_result(
            climate_financial_impact(
                cnae_code=reg.get("cnae_codigo"),
                climate_index=climate_index,
                revenue=fin.get("revenue"),
                ebit=fin.get("ebit"),
                ebitda=fin.get("ebitda"),
                market_cap=(mkt or {}).get("market_cap"),
                total_assets=fin.get("total_assets"),
                company_name=dossier.name or dossier.query,
            )
        )
    except Exception as exc:
        _record_error(dossier, "climate_financial", exc)
        dossier.climate_financial = {
            "status": "error",
            "reason": "falha interna no impacto financeiro climático",
        }


def _attach_supply_chain(dossier: Dossier) -> None:
    try:
        reg = dossier.registry or {}
        fin = dossier.financials or {}
        dossier.supply_chain = _section_result(
            supply_chain_climate_risk(
                value_chain=(dossier.relationships or {}).get("value_chain"),
                company_cnae=reg.get("cnae_codigo"),
                revenue=fin.get("revenue"),
                ebit=fin.get("ebit"),
                ebitda=fin.get("ebitda"),
                company_name=dossier.name or dossier.query,
            )
        )
    except Exception as exc:
        _record_error(dossier, "supply_chain", exc)
        dossier.supply_chain = {
            "status": "error",
            "reason": "falha interna no risco climático da cadeia",
        }


def dossier_status(payload: dict[str, Any]) -> str:
    if payload.get("errors"):
        return "degraded"
    for key in ("news", "market", "cross", "predictions", "climate_financial", "supply_chain"):
        section = payload.get(key)
        if isinstance(section, dict) and section.get("status") == "error":
            return "degraded"
    return "complete"


def _cached_payload(session: Session, key: str, now: dt.datetime) -> dict[str, Any] | None:
    row = session.get(CacheDossier, key)
    if row is not None and row.expires_at > now:
        payload = dict(row.payload)
        payload["cached"] = True
        return payload
    return None


def get_or_build_dossier(
    session: Session, query: str, *, ttl_s: int = 3600, max_news: int = 25
) -> dict[str, Any]:
    key = normalize_key(query)
    now = dt.datetime.now(dt.UTC)

    cached = _cached_payload(session, key, now)
    if cached is not None:
        return cached

    if session.get_bind().dialect.name == "postgresql":
        session.execute(
            sa.text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": key}
        )
        session.expire_all()
        cached = _cached_payload(session, key, now)
        if cached is not None:
            return cached

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
    _attach_analytics(session, dossier, analytics_cnpj)
    _attach_climate_financial(dossier)
    _attach_relationships(dossier, analytics_cnpj)
    _attach_supply_chain(dossier)

    payload = asdict(dossier)
    status = dossier_status(payload)
    payload["status"] = status
    effective_ttl = DEGRADED_TTL_S if status == "degraded" else ttl_s

    try:
        session.execute(sa.delete(CacheDossier).where(CacheDossier.expires_at <= now))
        session.merge(
            CacheDossier(
                query_key=key,
                kind=dossier.kind,
                payload=payload,
                expires_at=now + dt.timedelta(seconds=effective_ttl),
            )
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        log.warning("dossier.cache_write_failed", key=key, error=str(exc))

    payload["cached"] = False
    return payload
