from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from climate_esg.modeling.scoring import ScoreBand

_SUB_LABELS = {"policy": "política", "tech": "tecnológico", "market": "mercado"}


def risk_label(score: float) -> str:
    if score < 33:
        return "baixo"
    if score < 66:
        return "moderado"
    return "alto"


@dataclass(frozen=True, slots=True)
class Narrative:
    text: str
    drivers: dict[str, Any]


def _dominant_sub(sub_scores: dict[str, float | None]) -> tuple[str, float] | None:
    present = {k: v for k, v in sub_scores.items() if v is not None}
    if not present:
        return None
    key = max(present, key=lambda k: present[k])
    return key, present[key]


def build_narrative(
    *,
    company_name: str,
    scenario: str,
    horizon_year: int,
    physical: ScoreBand | None,
    transition: ScoreBand | None,
    composite: ScoreBand | None,
    sub_scores: dict[str, float | None],
    coverage_pct: float,
) -> Narrative:
    lines: list[str] = [f"**{company_name}** — cenário {scenario}, horizonte {horizon_year}."]

    if composite is not None:
        lines.append(
            f"Score composto **{composite.central:.0f}/100** "
            f"(faixa {composite.low:.0f}–{composite.high:.0f}), risco **{risk_label(composite.central)}**."
        )

    if physical is not None:
        lines.append(f"- Risco físico: {physical.central:.0f} ({risk_label(physical.central)})")
    if transition is not None:
        lines.append(
            f"- Risco de transição: {transition.central:.0f} ({risk_label(transition.central)})"
        )

    dominant_pillar: str | None = None
    if physical is not None and transition is not None:
        dominant_pillar = "físico" if physical.central >= transition.central else "transição"
        lines.append(f"Pilar dominante: **{dominant_pillar}**.")

    dom = _dominant_sub(sub_scores)
    if dom is not None:
        label = _SUB_LABELS.get(dom[0], dom[0])
        lines.append(f"Na transição, o sub-score dominante é **{label}** ({dom[1]:.0f}).")

    caveat = "boa" if coverage_pct >= 75 else "parcial" if coverage_pct >= 40 else "baixa"
    lines.append(
        f"Cobertura de dados: {coverage_pct:.0f}% ({caveat}) — banda de incerteza reflete essa cobertura."
    )

    drivers: dict[str, Any] = {
        "pilar_dominante": dominant_pillar,
        "sub_score_dominante": {"chave": dom[0], "valor": dom[1]} if dom else None,
        "coverage_pct": coverage_pct,
    }
    return Narrative(text="\n".join(lines), drivers=drivers)
