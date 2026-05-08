"""Score de risco de transição.

ADR-0004: no MVP é **soma ponderada calibrada**, não XGBoost. XGBoost só
volta na F3 Beta quando N for compatível com a métrica `AUC > 0.75 OOT`.
"""

from __future__ import annotations

from climate_esg.modeling.scoring import ScoreBand


def compute_transition_score(
    company_sk: int,
    scenario_sk: int,
    horizon_year: int,
) -> ScoreBand:
    """Stub MVP — soma ponderada de sub-scores política/tecnológica/mercado."""
    raise NotImplementedError(
        "transition_risk.compute_transition_score: aguardando F2 "
        "(coletor CDP/CVM + tabela de pesos calibrados)"
    )
