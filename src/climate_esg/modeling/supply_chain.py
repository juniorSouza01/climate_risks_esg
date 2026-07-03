from __future__ import annotations

from typing import Any

from climate_esg.ingestion.adaptabrasil import national_hazard_means
from climate_esg.modeling.climate_financial import sector_profile

# Afinidade hazard×setor: qual ameaça climática mais compromete a PRODUÇÃO de cada
# divisão CNAE fornecedora (seca destrói safra; enchente para fábrica/logística;
# deslizamento afeta mineração/encostas). Metodologia calibrável — selo INFERIDO.
_HAZARD_AFFINITY: dict[str, dict[str, float]] = {
    "01": {"seca": 0.70, "enchente": 0.20, "deslizamento": 0.10},
    "02": {"seca": 0.60, "enchente": 0.15, "deslizamento": 0.25},
    "03": {"seca": 0.50, "enchente": 0.40, "deslizamento": 0.10},
    "06": {"enchente": 0.50, "deslizamento": 0.30, "seca": 0.20},
    "07": {"enchente": 0.35, "deslizamento": 0.45, "seca": 0.20},
    "10": {"seca": 0.55, "enchente": 0.30, "deslizamento": 0.15},
    "13": {"seca": 0.55, "enchente": 0.30, "deslizamento": 0.15},
    "17": {"seca": 0.45, "enchente": 0.30, "deslizamento": 0.25},
    "19": {"enchente": 0.50, "deslizamento": 0.25, "seca": 0.25},
    "20": {"enchente": 0.45, "seca": 0.40, "deslizamento": 0.15},
    "23": {"enchente": 0.40, "seca": 0.35, "deslizamento": 0.25},
    "24": {"enchente": 0.40, "seca": 0.35, "deslizamento": 0.25},
    "25": {"enchente": 0.50, "seca": 0.30, "deslizamento": 0.20},
    "27": {"enchente": 0.50, "seca": 0.30, "deslizamento": 0.20},
    "35": {"seca": 0.60, "enchente": 0.25, "deslizamento": 0.15},
    "36": {"seca": 0.70, "enchente": 0.20, "deslizamento": 0.10},
    "46": {"enchente": 0.55, "deslizamento": 0.25, "seca": 0.20},
    "49": {"enchente": 0.55, "deslizamento": 0.30, "seca": 0.15},
}
_DEFAULT_AFFINITY = {"enchente": 0.40, "seca": 0.35, "deslizamento": 0.25}

_HAZARD_LABEL = {"seca": "seca/estresse hídrico", "enchente": "inundação", "deslizamento": "deslizamento"}


def _fragility(division: str | None) -> float:
    prof = sector_profile(division)
    return 0.5 * prof["raw_material"] + 0.3 * prof["asset"] + 0.2 * prof["revenue"]


def _band(central: float) -> dict[str, float]:
    return {
        "low": round(central * 0.5, 2),
        "central": round(central, 2),
        "high": round(central * 1.6, 2),
    }


def supply_chain_climate_risk(
    *,
    value_chain: dict[str, Any] | None,
    company_cnae: Any,
    revenue: float | None,
    ebit: float | None,
    ebitda: float | None,
    company_name: str = "empresa",
) -> dict[str, Any]:
    if not value_chain or not revenue or revenue <= 0:
        return {}
    upstream = value_chain.get("upstream") or []
    if not upstream:
        return {}

    try:
        means = national_hazard_means()
    except Exception:
        means = {}
    if not means:
        return {}

    max_fragility = 0.17  # agropecuária ≈ teto da escala de fragilidade
    suppliers: list[dict[str, Any]] = []
    for item in upstream:
        division = item.get("division")
        affinity = _HAZARD_AFFINITY.get(division or "", _DEFAULT_AFFINITY)
        exposure = sum(affinity.get(h, 0.0) * v for h, v in means.items())
        dominant = max(affinity, key=lambda h: affinity[h] * means.get(h, 0.0))
        frag = _fragility(division)
        disruption = min(1.0, exposure * min(1.0, frag / max_fragility))
        suppliers.append(
            {
                "division": division,
                "label": item.get("label"),
                "archetype": sector_profile(division)["archetype"] if division else None,
                "dominant_hazard": _HAZARD_LABEL.get(dominant, dominant),
                "exposure_index": round(exposure * 100, 1),
                "fragility": round(frag, 3),
                "disruption_index": round(disruption * 100, 1),
            }
        )

    chain_index = sum(s["disruption_index"] for s in suppliers) / len(suppliers)

    company_prof = sector_profile(company_cnae)
    dependence = company_prof["raw_material"]
    cogs_proxy = revenue - ebit if (ebit is not None) else revenue * 0.70
    production_at_risk = cogs_proxy * (chain_index / 100.0) * dependence
    pct_ebitda = (production_at_risk / ebitda * 100.0) if ebitda and ebitda > 0 else None

    worst = max(suppliers, key=lambda s: s["disruption_index"])
    narrative = _narrative(
        company_name, company_prof, worst, chain_index, production_at_risk, pct_ebitda
    )

    return {
        "suppliers": suppliers,
        "chain_risk_index": round(chain_index, 1),
        "dependence_raw_material": dependence,
        "production_at_risk_brl": _band(production_at_risk),
        "production_at_risk_pct_ebitda": round(pct_ebitda, 1) if pct_ebitda is not None else None,
        "national_hazard_means": {k: round(v * 100, 1) for k, v in means.items()},
        "methodology": (
            "Setores fornecedores típicos (CNAE, não contrapartes reais) × exposição "
            "climática média nacional (AdaptaBrasil, SSP5-8.5/2050) × fragilidade "
            "setorial do fornecedor × dependência de insumos da empresa."
        ),
        "narrative": narrative,
        "seal": "inferido",
    }


def _narrative(
    name: str,
    company_prof: dict[str, Any],
    worst: dict[str, Any],
    chain_index: float,
    production_at_risk: float,
    pct_ebitda: float | None,
) -> str:
    lines = [
        f"**Risco climático na cadeia de suprimentos — {name}**",
        f"- Elo mais frágil a montante: **{worst['label']}** — ameaça dominante "
        f"**{worst['dominant_hazard']}** (exposição {worst['exposure_index']:.0f}/100, "
        f"disrupção {worst['disruption_index']:.0f}/100).",
        f"- Se esse fornecimento falha, a produção de **{company_prof['archetype']}** para: "
        f"perda potencial de produção ~**{_brl(production_at_risk)}**"
        + (f" (**{pct_ebitda:.0f}% do EBITDA**)." if pct_ebitda is not None else "."),
        f"- Índice de risco da cadeia: **{chain_index:.0f}/100** — setores típicos e exposição "
        "média nacional; fornecedores reais e suas localizações refinariam a conta.",
    ]
    return "\n".join(lines)


def _brl(v: float) -> str:
    if abs(v) >= 1e9:
        return f"R$ {v / 1e9:.2f} bi"
    if abs(v) >= 1e6:
        return f"R$ {v / 1e6:.2f} mi"
    if abs(v) >= 1e3:
        return f"R$ {v / 1e3:.0f} mil"
    return f"R$ {v:.0f}"
