from __future__ import annotations

from typing import Any

from climate_esg.modeling.physical_config import severity_label

# Perfis de sensibilidade por setor (divisão CNAE, 2 primeiros dígitos).
# Cada canal (0..1) = fração MÁXIMA daquela linha exposta a risco físico pleno.
# Metodologia calibrável (estilo TCFD/NGFS) — NÃO é dado de empresa. Selo INFERIDO.
# Canais: raw_material (matéria-prima/COGS), asset (ativos/impairment),
#         revenue (demanda/disrupção), transition (carbono/política).
_DEFAULT = {
    "archetype": "Setor geral",
    "raw_material": 0.10,
    "asset": 0.08,
    "revenue": 0.08,
    "transition": 0.08,
}

_PROFILES: dict[str, dict[str, Any]] = {
    "01": {"archetype": "Agropecuária", "raw_material": 0.25, "asset": 0.10, "revenue": 0.12, "transition": 0.05},
    "02": {"archetype": "Produção florestal", "raw_material": 0.24, "asset": 0.10, "revenue": 0.10, "transition": 0.05},
    "03": {"archetype": "Pesca/aquicultura", "raw_material": 0.24, "asset": 0.08, "revenue": 0.12, "transition": 0.05},
    "05": {"archetype": "Extração de carvão", "raw_material": 0.15, "asset": 0.12, "revenue": 0.08, "transition": 0.30},
    "06": {"archetype": "Petróleo e gás", "raw_material": 0.10, "asset": 0.15, "revenue": 0.08, "transition": 0.35},
    "07": {"archetype": "Mineração", "raw_material": 0.20, "asset": 0.18, "revenue": 0.08, "transition": 0.15},
    "08": {"archetype": "Mineração (não-metálicos)", "raw_material": 0.20, "asset": 0.16, "revenue": 0.08, "transition": 0.15},
    "10": {"archetype": "Alimentos", "raw_material": 0.22, "asset": 0.08, "revenue": 0.10, "transition": 0.06},
    "11": {"archetype": "Bebidas", "raw_material": 0.18, "asset": 0.08, "revenue": 0.10, "transition": 0.06},
    "13": {"archetype": "Têxtil", "raw_material": 0.22, "asset": 0.08, "revenue": 0.08, "transition": 0.08},
    "14": {"archetype": "Confecção/vestuário", "raw_material": 0.18, "asset": 0.06, "revenue": 0.10, "transition": 0.06},
    "16": {"archetype": "Madeira", "raw_material": 0.22, "asset": 0.10, "revenue": 0.08, "transition": 0.08},
    "17": {"archetype": "Celulose e papel", "raw_material": 0.18, "asset": 0.12, "revenue": 0.08, "transition": 0.12},
    "19": {"archetype": "Refino/combustíveis", "raw_material": 0.12, "asset": 0.15, "revenue": 0.08, "transition": 0.35},
    "20": {"archetype": "Química", "raw_material": 0.18, "asset": 0.12, "revenue": 0.08, "transition": 0.20},
    "21": {"archetype": "Farmacêutica", "raw_material": 0.10, "asset": 0.08, "revenue": 0.05, "transition": 0.06},
    "22": {"archetype": "Plásticos/borracha", "raw_material": 0.16, "asset": 0.08, "revenue": 0.08, "transition": 0.14},
    "23": {"archetype": "Cimento/materiais", "raw_material": 0.15, "asset": 0.15, "revenue": 0.08, "transition": 0.30},
    "24": {"archetype": "Siderurgia/metalurgia", "raw_material": 0.15, "asset": 0.15, "revenue": 0.08, "transition": 0.28},
    "25": {"archetype": "Produtos de metal", "raw_material": 0.14, "asset": 0.08, "revenue": 0.08, "transition": 0.12},
    "26": {"archetype": "Eletrônicos", "raw_material": 0.10, "asset": 0.06, "revenue": 0.08, "transition": 0.06},
    "27": {"archetype": "Equipamentos elétricos", "raw_material": 0.12, "asset": 0.07, "revenue": 0.08, "transition": 0.08},
    "28": {"archetype": "Máquinas e equipamentos", "raw_material": 0.12, "asset": 0.08, "revenue": 0.08, "transition": 0.10},
    "29": {"archetype": "Automotivo", "raw_material": 0.12, "asset": 0.08, "revenue": 0.10, "transition": 0.18},
    "31": {"archetype": "Móveis", "raw_material": 0.18, "asset": 0.07, "revenue": 0.08, "transition": 0.06},
    "35": {"archetype": "Energia elétrica", "raw_material": 0.06, "asset": 0.18, "revenue": 0.08, "transition": 0.18},
    "36": {"archetype": "Água/saneamento", "raw_material": 0.10, "asset": 0.18, "revenue": 0.08, "transition": 0.06},
    "41": {"archetype": "Construção", "raw_material": 0.15, "asset": 0.15, "revenue": 0.10, "transition": 0.10},
    "42": {"archetype": "Infraestrutura/obras", "raw_material": 0.15, "asset": 0.16, "revenue": 0.10, "transition": 0.10},
    "45": {"archetype": "Comércio de veículos", "raw_material": 0.06, "asset": 0.06, "revenue": 0.10, "transition": 0.08},
    "46": {"archetype": "Comércio atacadista", "raw_material": 0.08, "asset": 0.06, "revenue": 0.10, "transition": 0.06},
    "47": {"archetype": "Varejo", "raw_material": 0.08, "asset": 0.06, "revenue": 0.12, "transition": 0.05},
    "49": {"archetype": "Transporte terrestre", "raw_material": 0.06, "asset": 0.12, "revenue": 0.10, "transition": 0.18},
    "50": {"archetype": "Transporte aquaviário", "raw_material": 0.06, "asset": 0.12, "revenue": 0.10, "transition": 0.18},
    "51": {"archetype": "Transporte aéreo", "raw_material": 0.06, "asset": 0.12, "revenue": 0.10, "transition": 0.22},
    "55": {"archetype": "Hotelaria", "raw_material": 0.06, "asset": 0.10, "revenue": 0.14, "transition": 0.05},
    "58": {"archetype": "Editorial/mídia", "raw_material": 0.04, "asset": 0.05, "revenue": 0.06, "transition": 0.04},
    "61": {"archetype": "Telecomunicações", "raw_material": 0.04, "asset": 0.08, "revenue": 0.05, "transition": 0.05},
    "62": {"archetype": "Tecnologia/software", "raw_material": 0.03, "asset": 0.04, "revenue": 0.05, "transition": 0.04},
    "63": {"archetype": "Serviços de informação", "raw_material": 0.03, "asset": 0.04, "revenue": 0.05, "transition": 0.04},
    "64": {"archetype": "Serviços financeiros", "raw_material": 0.03, "asset": 0.03, "revenue": 0.04, "transition": 0.06},
    "65": {"archetype": "Seguros/previdência", "raw_material": 0.03, "asset": 0.04, "revenue": 0.06, "transition": 0.06},
    "66": {"archetype": "Serviços financeiros aux.", "raw_material": 0.03, "asset": 0.03, "revenue": 0.05, "transition": 0.05},
    "68": {"archetype": "Imobiliário", "raw_material": 0.05, "asset": 0.20, "revenue": 0.08, "transition": 0.06},
    "85": {"archetype": "Educação", "raw_material": 0.04, "asset": 0.06, "revenue": 0.06, "transition": 0.04},
    "86": {"archetype": "Saúde", "raw_material": 0.06, "asset": 0.08, "revenue": 0.06, "transition": 0.05},
}


def sector_profile(cnae_code: Any) -> dict[str, Any]:
    if cnae_code is None:
        return {**_DEFAULT, "division": None, "assumed": True}
    digits = "".join(c for c in str(cnae_code) if c.isdigit())
    division = digits[:2] if len(digits) >= 2 else None
    profile = _PROFILES.get(division or "", _DEFAULT)
    return {**profile, "division": division, "assumed": division not in _PROFILES}


def _band(central: float) -> dict[str, float]:
    return {
        "low": round(central * 0.5, 2),
        "central": round(central, 2),
        "high": round(central * 1.6, 2),
    }


def climate_financial_impact(
    *,
    cnae_code: Any,
    climate_index: float | None,
    revenue: float | None,
    ebit: float | None,
    ebitda: float | None,
    market_cap: float | None = None,
    total_assets: float | None = None,
    company_name: str = "empresa",
) -> dict[str, Any]:
    if climate_index is None:
        return {"status": "no_input", "reason": "sem índice climático da sede"}
    if not revenue or revenue <= 0:
        return {"status": "no_input", "reason": "sem receita positiva"}

    prof = sector_profile(cnae_code)
    exposure = max(0.0, min(1.0, climate_index / 100.0))

    ebitda_margin = (ebitda / revenue) if (ebitda and revenue) else 0.15
    cogs_proxy = revenue - ebit if (ebit is not None) else revenue * 0.70
    if total_assets and total_assets > 0:
        asset_proxy = total_assets
        asset_basis = "ativos totais (balanço CVM)"
    elif market_cap and market_cap > 0:
        asset_proxy = market_cap
        asset_basis = "market cap (proxy)"
    else:
        asset_proxy = revenue
        asset_basis = "receita (proxy)"

    receita_risk = revenue * exposure * prof["revenue"]
    materia_risk = cogs_proxy * exposure * prof["raw_material"]
    # EBITDA sofre pela margem da receita perdida + aumento pleno de custo de insumo
    ebitda_risk = receita_risk * max(0.0, ebitda_margin) + materia_risk
    ativos_risk = asset_proxy * exposure * prof["asset"]
    roi_reduction_pp = (ebitda_risk / asset_proxy) * 100.0 if asset_proxy else 0.0

    channels = {
        "receita": {
            "label": "Receita em risco (demanda/disrupção)",
            "statement": "DRE",
            "brl": _band(receita_risk),
            "pct_base": round(100 * receita_risk / revenue, 2),
        },
        "materia_prima": {
            "label": "Matéria-prima / custos (COGS) em risco",
            "statement": "DRE",
            "brl": _band(materia_risk),
            "pct_base": round(100 * materia_risk / cogs_proxy, 2) if cogs_proxy else 0.0,
        },
        "ebitda": {
            "label": "EBITDA em risco (compressão de margem)",
            "statement": "DRE",
            "brl": _band(ebitda_risk),
            "pct_base": round(100 * ebitda_risk / ebitda, 2) if ebitda else None,
        },
        "ativos": {
            "label": f"Impairment de ativos — base: {asset_basis}",
            "statement": "Balanço",
            "brl": _band(ativos_risk),
            "pct_base": round(100 * ativos_risk / asset_proxy, 2) if asset_proxy else 0.0,
        },
        "roi": {
            "label": "Redução de ROI (p.p.)",
            "statement": "Retorno",
            "pp": _band(roi_reduction_pp),
        },
    }

    # Materialidade: quanto do EBITDA está em risco (0..1). Amplifica o risco climático.
    materialidade = 0.0
    if ebitda and ebitda > 0:
        materialidade = max(0.0, min(1.0, ebitda_risk / ebitda))
    else:
        materialidade = max(0.0, min(1.0, receita_risk / revenue))

    risco_ajustado = min(100.0, climate_index * (1.0 + materialidade))
    label = severity_label(risco_ajustado)

    narrative = _narrative(company_name, prof, climate_index, materialidade, risco_ajustado, channels)

    return {
        "status": "ok",
        "reason": None,
        "sector": {
            "cnae": str(cnae_code) if cnae_code is not None else None,
            "division": prof.get("division"),
            "archetype": prof["archetype"],
            "assumed": prof.get("assumed", False),
            "sensitivities": {
                "raw_material": prof["raw_material"],
                "asset": prof["asset"],
                "revenue": prof["revenue"],
                "transition": prof["transition"],
            },
        },
        "physical_exposure": round(exposure, 3),
        "climate_index": round(climate_index, 1),
        "channels": channels,
        "materialidade": round(materialidade, 3),
        "risco_ajustado": {
            "value": round(risco_ajustado, 1),
            "label": label,
            "basis": "índice climático × (1 + materialidade financeira)",
        },
        "narrative": narrative,
        "seal": "inferido",
    }


def _narrative(
    name: str,
    prof: dict[str, Any],
    climate_index: float,
    materialidade: float,
    risco_ajustado: float,
    channels: dict[str, Any],
) -> str:
    eb = channels["ebitda"]["brl"]["central"]
    mp = channels["materia_prima"]["brl"]["central"]
    lines = [
        f"**Risco climático × financeiro — {name}**",
        f"- Modelo de negócio: **{prof['archetype']}** — define a sensibilidade a clima "
        f"(matéria-prima {int(prof['raw_material'] * 100)}%, ativos {int(prof['asset'] * 100)}%, "
        f"transição {int(prof['transition'] * 100)}%).",
        f"- Índice climático da sede **{climate_index:.0f}/100**; **materialidade financeira "
        f"{materialidade * 100:.0f}%** do EBITDA exposto → **risco ajustado {risco_ajustado:.0f}/100**.",
        f"- Impacto estimado (central): EBITDA em risco ~**{_brl(eb)}**, matéria-prima/COGS ~**{_brl(mp)}**.",
        "- Estimativa de sensibilidade (coeficientes setoriais calibráveis), não perda modelada por ativo.",
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
