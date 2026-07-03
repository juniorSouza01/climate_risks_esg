from __future__ import annotations

import io
import unicodedata
import zipfile
from typing import Any

import pandas as pd
import sqlalchemy as sa
from sqlalchemy.orm import Session

from climate_esg.db.models import CompanyFinancials, CvmFinancials, DimCompany
from climate_esg.ingestion.geocoding import only_digits
from climate_esg.ingestion.http import get_client

DFP_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{year}.zip"

_STOPWORDS = {"SA", "S", "A", "CIA", "COMPANHIA", "PARTICIPACOES", "PART", "HOLDING"}
_REVENUE_ACCOUNT = "3.01"
_EBIT_ACCOUNT = "3.05"
_NET_INCOME_ACCOUNT = "3.11"


def _strip_accents(value: Any) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", str(value)) if not unicodedata.combining(c)
    ).upper()


def normalize_name(name: str) -> str:
    stripped = _strip_accents(name)
    tokens = "".join(ch if ch.isalnum() else " " for ch in stripped).split()
    kept = [t for t in tokens if t not in _STOPWORDS]
    return " ".join(kept)


def _to_float(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return None


def _scale(escala: Any) -> float:
    return 1000.0 if "MIL" in _strip_accents(escala) else 1.0


def _balance_by_cnpj(zf: zipfile.ZipFile) -> dict[str, dict[str, float | None]]:
    out: dict[str, dict[str, float | None]] = {}
    for kind, member_key, accounts in (
        ("bpa", "BPA_con", {"total_assets": ("1",)}),
        ("bpp", "BPP_con", {"equity": ("2.03",), "gross_debt": ("2.01.04", "2.02.01")}),
    ):
        member = next((n for n in zf.namelist() if member_key in n), None)
        if member is None:
            continue
        with zf.open(member) as fh:
            df = pd.read_csv(fh, sep=";", encoding="latin-1", dtype=str)
        df = df[df["ORDEM_EXERC"] == "ÚLTIMO"]
        for cnpj_raw, grp in df.groupby("CNPJ_CIA"):
            latest = grp["DT_REFER"].max()
            g = grp[grp["DT_REFER"] == latest]
            cnpj = only_digits(str(cnpj_raw))
            rec = out.setdefault(cnpj, {})
            for field, codes in accounts.items():
                total: float | None = None
                for code in codes:
                    row = g[g["CD_CONTA"] == code]
                    if row.empty:
                        continue
                    v = _to_float(row.iloc[0]["VL_CONTA"])
                    if v is not None:
                        scaled = v * _scale(row.iloc[0].get("ESCALA_MOEDA"))
                        total = scaled if total is None else total + scaled
                rec[field] = total
    return out


def _da_by_cnpj(zf: zipfile.ZipFile) -> dict[str, float]:
    member = next((n for n in zf.namelist() if "DFC_MI_con" in n), None)
    if member is None:
        return {}
    with zf.open(member) as fh:
        df = pd.read_csv(fh, sep=";", encoding="latin-1", dtype=str)
    df = df[df["ORDEM_EXERC"] == "ÚLTIMO"]
    mask = df["DS_CONTA"].map(
        lambda s: "DEPRECIA" in _strip_accents(s) or "AMORTIZA" in _strip_accents(s)
    )
    df = df[mask]
    out: dict[str, float] = {}
    for cnpj_raw, grp in df.groupby("CNPJ_CIA"):
        latest = grp["DT_REFER"].max()
        g = grp[grp["DT_REFER"] == latest]
        total = 0.0
        for _, row in g.iterrows():
            v = _to_float(row["VL_CONTA"])
            if v is not None:
                total += abs(v) * _scale(row.get("ESCALA_MOEDA"))
        out[only_digits(str(cnpj_raw))] = total
    return out


def fetch_dfp_financials(year: int, *, timeout: float = 180.0) -> dict[str, dict[str, Any]]:
    resp = get_client().get(DFP_URL.format(year=year), timeout=timeout)
    resp.raise_for_status()
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    member = next((n for n in zf.namelist() if "DRE_con" in n), None)
    if member is None:
        return {}
    with zf.open(member) as fh:
        df = pd.read_csv(fh, sep=";", encoding="latin-1", dtype=str)

    df = df[df["ORDEM_EXERC"] == "ÚLTIMO"]
    da_map = _da_by_cnpj(zf)
    balance = _balance_by_cnpj(zf)
    out: dict[str, dict[str, Any]] = {}
    for denom, group in df.groupby("DENOM_CIA"):
        latest = group["DT_REFER"].max()
        g = group[group["DT_REFER"] == latest]
        cnpj = only_digits(str(g.iloc[0]["CNPJ_CIA"]))
        scale = _scale(g.iloc[0].get("ESCALA_MOEDA"))

        def _acct(code: str, g: pd.DataFrame = g, scale: float = scale) -> float | None:
            row = g[g["CD_CONTA"] == code]
            if row.empty:
                return None
            v = _to_float(row.iloc[0]["VL_CONTA"])
            return None if v is None else v * scale

        ebit = _acct(_EBIT_ACCOUNT)
        da = da_map.get(cnpj)
        ebitda = ebit + da if (ebit is not None and da is not None) else None
        bal = balance.get(cnpj, {})
        out[cnpj] = {
            "cnpj": cnpj,
            "denom": str(denom)[:200],
            "denom_norm": normalize_name(str(denom))[:200],
            "revenue": _acct(_REVENUE_ACCOUNT),
            "ebit": ebit,
            "ebitda": ebitda,
            "net_income": _acct(_NET_INCOME_ACCOUNT),
            "total_assets": bal.get("total_assets"),
            "equity": bal.get("equity"),
            "gross_debt": bal.get("gross_debt"),
            "fiscal_year": int(str(latest)[:4]),
        }
    return out


def _upsert_cvm_all(session: Session, financials: dict[str, dict[str, Any]], year: int) -> int:
    n = 0
    for cnpj, rec in financials.items():
        if not cnpj:
            continue
        existing = session.scalar(
            sa.select(CvmFinancials).where(
                CvmFinancials.cnpj == cnpj,
                CvmFinancials.fiscal_year == rec["fiscal_year"],
            )
        )
        if existing is not None:
            existing.denom = rec["denom"]
            existing.denom_norm = rec["denom_norm"]
            existing.revenue = rec["revenue"]
            existing.ebit = rec["ebit"]
            existing.ebitda = rec["ebitda"]
            existing.net_income = rec["net_income"]
            existing.total_assets = rec.get("total_assets")
            existing.equity = rec.get("equity")
            existing.gross_debt = rec.get("gross_debt")
        else:
            session.add(
                CvmFinancials(
                    cnpj=cnpj,
                    denom=rec["denom"],
                    denom_norm=rec["denom_norm"],
                    fiscal_year=rec["fiscal_year"],
                    revenue=rec["revenue"],
                    ebit=rec["ebit"],
                    ebitda=rec["ebitda"],
                    net_income=rec["net_income"],
                    total_assets=rec.get("total_assets"),
                    equity=rec.get("equity"),
                    gross_debt=rec.get("gross_debt"),
                    source=f"cvm_dfp_{year}",
                )
            )
        n += 1
    return n


def ingest_cvm_financials(session: Session, year: int) -> int:
    financials = fetch_dfp_financials(year)
    _upsert_cvm_all(session, financials, year)

    by_name = {rec["denom_norm"]: rec for rec in financials.values()}
    companies = session.execute(sa.select(DimCompany.company_sk, DimCompany.name)).all()
    matched = 0
    for company_sk, name in companies:
        rec = by_name.get(normalize_name(str(name)))
        if rec is None:
            continue
        existing = session.scalar(
            sa.select(CompanyFinancials).where(
                CompanyFinancials.company_sk == company_sk,
                CompanyFinancials.fiscal_year == rec["fiscal_year"],
            )
        )
        if existing is not None:
            existing.revenue = rec["revenue"]
            existing.net_income = rec["net_income"]
            existing.cnpj = rec["cnpj"]
        else:
            session.add(
                CompanyFinancials(
                    company_sk=company_sk,
                    fiscal_year=rec["fiscal_year"],
                    revenue=rec["revenue"],
                    net_income=rec["net_income"],
                    cnpj=rec["cnpj"],
                    source=f"cvm_dfp_{year}",
                )
            )
        matched += 1
    return matched
