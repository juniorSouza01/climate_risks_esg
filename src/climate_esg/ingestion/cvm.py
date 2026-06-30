from __future__ import annotations

import io
import unicodedata
import zipfile
from typing import Any

import pandas as pd
import sqlalchemy as sa
from sqlalchemy.orm import Session

from climate_esg.db.models import CompanyFinancials, DimCompany
from climate_esg.ingestion.geocoding import only_digits
from climate_esg.ingestion.http import get_client

DFP_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{year}.zip"

_STOPWORDS = {"SA", "S", "A", "CIA", "COMPANHIA", "PARTICIPACOES", "PART", "HOLDING"}
_REVENUE_ACCOUNT = "3.01"
_NET_INCOME_ACCOUNT = "3.11"


def normalize_name(name: str) -> str:
    stripped = "".join(
        c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c)
    ).upper()
    tokens = [t for t in "".join(ch if ch.isalnum() else " " for ch in stripped).split()]
    kept = [t for t in tokens if t not in _STOPWORDS]
    return " ".join(kept)


def _to_float(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return None


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
    out: dict[str, dict[str, Any]] = {}
    for denom, group in df.groupby("DENOM_CIA"):
        latest = group["DT_REFER"].max()
        g = group[group["DT_REFER"] == latest]

        def _acct(code: str, g: pd.DataFrame = g) -> float | None:
            row = g[g["CD_CONTA"] == code]
            return None if row.empty else _to_float(row.iloc[0]["VL_CONTA"])

        out[normalize_name(str(denom))] = {
            "revenue": _acct(_REVENUE_ACCOUNT),
            "net_income": _acct(_NET_INCOME_ACCOUNT),
            "cnpj": only_digits(str(g.iloc[0]["CNPJ_CIA"])),
            "fiscal_year": int(str(latest)[:4]),
        }
    return out


def ingest_cvm_financials(session: Session, year: int) -> int:
    financials = fetch_dfp_financials(year)
    companies = session.execute(sa.select(DimCompany.company_sk, DimCompany.name)).all()
    matched = 0
    for company_sk, name in companies:
        rec = financials.get(normalize_name(str(name)))
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
