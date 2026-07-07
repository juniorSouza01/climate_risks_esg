from __future__ import annotations

import math
from typing import Any

import numpy as np
import sqlalchemy as sa
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from climate_esg.db.models import CvmFinancials
from climate_esg.ingestion.geocoding import only_digits
from climate_esg.modeling.physical_config import (
    ADAPTABRASIL_HAZARD_WEIGHTS,
    DEFAULT_HAZARD_WEIGHT,
    severity_label,
)

MIN_SAMPLE = 10
# Sensibilidade da receita à ameaça climática — heurística DECLARADA (placeholder F1),
# não medição calibrada. Faixa low/central/high da fração de receita exposta por unidade.
_SENSITIVITY = (0.03, 0.08, 0.15)
_FEATURES = ("log_revenue", "ebitda_margin", "net_margin")


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _load_universe(session: Session) -> list[dict[str, Any]]:
    rows = session.execute(
        sa.select(
            CvmFinancials.cnpj,
            CvmFinancials.denom,
            CvmFinancials.revenue,
            CvmFinancials.ebitda,
            CvmFinancials.net_income,
        )
    ).all()
    out: list[dict[str, Any]] = []
    for cnpj, denom, revenue, ebitda, net_income in rows:
        rev = float(revenue) if revenue is not None else None
        if not rev or rev <= 0:
            continue
        eb = float(ebitda) if ebitda is not None else None
        ni = float(net_income) if net_income is not None else None
        out.append(
            {
                "cnpj": cnpj,
                "denom": denom,
                "revenue": rev,
                "ebitda": eb,
                "net_income": ni,
                "log_revenue": math.log10(rev),
                "ebitda_margin": _clip(eb / rev, -2.0, 2.0) if eb is not None else None,
                "net_margin": _clip(ni / rev, -2.0, 2.0) if ni is not None else None,
            }
        )
    return out


def _percentile(values: list[float], target: float) -> float:
    if not values:
        return 0.0
    below = sum(1 for v in values if v <= target)
    return round(100.0 * below / len(values), 1)


def _climate_index(climate_risk: dict[str, Any] | None) -> float | None:
    if not climate_risk:
        return None
    num = 0.0
    den = 0.0
    for hazard, r in climate_risk.items():
        w = ADAPTABRASIL_HAZARD_WEIGHTS.get(hazard, DEFAULT_HAZARD_WEIGHT)
        val = r.get("value") if isinstance(r, dict) else None
        if val is None:
            continue
        v = float(val) * 100.0
        num += w * v
        den += w
    if den == 0:
        return None
    return round(num / den, 1)


def _cluster_label(median_rev: float, median_margin: float | None) -> str:
    if median_rev >= 1e10:
        porte = "grande porte"
    elif median_rev >= 1e9:
        porte = "médio-grande porte"
    elif median_rev >= 1e8:
        porte = "médio porte"
    else:
        porte = "menor porte"
    if median_margin is None:
        return porte
    if median_margin >= 0.20:
        margem = "margem alta"
    elif median_margin >= 0.08:
        margem = "margem média"
    elif median_margin >= 0:
        margem = "margem baixa"
    else:
        margem = "margem negativa"
    return f"{porte}, {margem}"


def _build_narrative(cross: dict[str, Any], name: str) -> str:
    lines = [f"**Cruzamento — {name}**"]
    ci = cross.get("climate_index")
    rar = cross.get("revenue_at_risk")
    rp = cross.get("revenue_percentile")
    if ci is not None:
        lines.append(
            f"- Índice de ameaça climática da sede: **{ci['value']:.0f}/100** ({ci['label']})."
        )
    if rar is not None:
        lines.append(
            f"- Receita-em-risco estimada: **{rar['pct_central']:.1f}%** da receita "
            f"(faixa {rar['pct_low']:.1f}–{rar['pct_high']:.1f}%) — heurística, não perda modelada."
        )
    if rp is not None:
        lines.append(
            f"- Receita no **percentil {rp['value']:.0f}** de {rp['n']} cias abertas (CVM)."
        )
    return "\n".join(lines)


def analyze_company(
    session: Session,
    cnpj: str | None,
    *,
    name: str = "empresa",
    climate_risk: dict[str, Any] | None = None,
    revenue: float | None = None,
) -> dict[str, Any]:
    universe = _load_universe(session)
    if len(universe) < MIN_SAMPLE:
        return {
            "status": "insufficient_universe",
            "reason": f"universo CVM com {len(universe)} empresas (mínimo {MIN_SAMPLE})",
        }

    cnpjs = [only_digits(str(d["cnpj"] or "")) for d in universe]
    target_key = only_digits(str(cnpj)) if cnpj else None
    target_idx = cnpjs.index(target_key) if (target_key and target_key in cnpjs) else None
    target = universe[target_idx] if target_idx is not None else None
    rev = target["revenue"] if target else revenue

    cross: dict[str, Any] = {}

    ci = _climate_index(climate_risk)
    if ci is not None:
        cross["climate_index"] = {
            "value": ci,
            "label": severity_label(ci),
            "basis": "sede municipal",
        }
        if rev:
            frac = ci / 100.0
            cross["revenue_at_risk"] = {
                "pct_low": round(_SENSITIVITY[0] * frac * 100, 2),
                "pct_central": round(_SENSITIVITY[1] * frac * 100, 2),
                "pct_high": round(_SENSITIVITY[2] * frac * 100, 2),
                "brl_low": rev * _SENSITIVITY[0] * frac,
                "brl_central": rev * _SENSITIVITY[1] * frac,
                "brl_high": rev * _SENSITIVITY[2] * frac,
                "basis": "receita × ameaça municipal × sensibilidade setorial",
                "seal": "inferido",
            }

    if rev:
        revenues = [d["revenue"] for d in universe]
        cross["revenue_percentile"] = {
            "value": _percentile(revenues, rev),
            "n": len(revenues),
            "basis": "universo CVM",
        }
    margins = [d["ebitda_margin"] for d in universe if d["ebitda_margin"] is not None]
    if target and target["ebitda_margin"] is not None and margins:
        cross["ebitda_margin_percentile"] = {
            "value": _percentile(margins, target["ebitda_margin"]),
            "n": len(margins),
            "basis": "universo CVM (com EBITDA)",
        }

    cross["narrative"] = _build_narrative(cross, name)

    predictions: dict[str, Any] = {}
    if target_idx is not None and len(universe) >= 20:
        raw = np.array(
            [[d[f] if d[f] is not None else np.nan for f in _FEATURES] for d in universe],
            dtype=float,
        )
        col_median = np.nanmedian(raw, axis=0)
        nan_pos = np.where(np.isnan(raw))
        raw[nan_pos] = np.take(col_median, nan_pos[1])
        X = StandardScaler().fit_transform(raw)

        k = min(5, len(universe) // 4)
        km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
        labels = km.labels_
        target_cluster = int(labels[target_idx])
        members = [i for i, c in enumerate(labels) if c == target_cluster]
        median_rev = float(np.median([universe[i]["revenue"] for i in members]))
        cl_margins = [
            universe[i]["ebitda_margin"]
            for i in members
            if universe[i]["ebitda_margin"] is not None
        ]
        median_margin = float(np.median(cl_margins)) if cl_margins else None
        predictions["segment"] = {
            "cluster": target_cluster,
            "label": _cluster_label(median_rev, median_margin),
            "n_in_cluster": len(members),
            "n_total": len(universe),
            "basis": "K-Means sobre receita/margens (reflete porte×margem, não perfil ESG)",
            "seal": "previsto",
        }

        n_neighbors = min(6, len(universe))
        nn = NearestNeighbors(n_neighbors=n_neighbors).fit(X)
        dist, idxs = nn.kneighbors(X[target_idx : target_idx + 1])
        peers = []
        for d, i in zip(dist[0], idxs[0], strict=False):
            if int(i) == target_idx:
                continue
            peers.append(
                {
                    "cnpj": universe[i]["cnpj"],
                    "denom": universe[i]["denom"],
                    "distance": round(float(d), 3),
                }
            )
        predictions["peers"] = {
            "items": peers[:5],
            "basis": "vizinhos por perfil financeiro (receita/margens)",
            "seal": "previsto",
        }

        iso = IsolationForest(random_state=42, n_estimators=200).fit(X)
        is_outlier = bool(iso.predict(X[target_idx : target_idx + 1])[0] == -1)
        score = float(iso.score_samples(X[target_idx : target_idx + 1])[0])
        predictions["anomaly"] = {
            "is_outlier": is_outlier,
            "score": round(score, 3),
            "basis": "IsolationForest sobre o universo CVM",
            "seal": "previsto",
        }

    return {"status": "ok", "reason": None, "cross": cross, "predictions": predictions}
