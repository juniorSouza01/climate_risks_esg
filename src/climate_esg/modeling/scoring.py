"""Composição final de score (placeholder).

A implementação real entra na F1. Este módulo serve para ancorar os tipos
e o contrato (entrada/saída) que outras camadas (api, governance) podem
referenciar desde já.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScoreBand:
    """Score sempre entregue como banda (princípio §2.2.4 do project.md)."""

    central: float
    low: float
    high: float

    def __post_init__(self) -> None:
        if not (0 <= self.low <= self.central <= self.high <= 100):
            raise ValueError(
                f"banda inválida: low={self.low} central={self.central} high={self.high}"
            )


def clamp(value: float, low: float, high: float) -> float:
    """Limita ``value`` ao intervalo [low, high]."""
    return max(low, min(high, value))


def normalize_linear(value: float, ref_low: float, ref_high: float) -> float:
    """Mapeia ``value`` para 0–100 linearmente entre ref_low e ref_high (clampeado).

    ``ref_low`` → 0, ``ref_high`` → 100. Se ref_low == ref_high, retorna 50
    (sem informação para discriminar). Suporta faixa invertida (ref_low >
    ref_high) para indicadores em que "menor é pior".
    """
    if ref_low == ref_high:
        return 50.0
    pct = (value - ref_low) / (ref_high - ref_low) * 100.0
    return clamp(pct, 0.0, 100.0)


def weighted_score_band(
    subscores: Mapping[str, float],
    weights: Mapping[str, float],
    *,
    base_uncertainty: float = 5.0,
    coverage_penalty: float = 20.0,
) -> ScoreBand:
    """Combina sub-scores (0–100) por soma ponderada, retornando uma banda.

    Princípio §2.2.4: o score é faixa, nunca ponto. A largura da banda cresce
    com (a) discordância entre hazards e (b) baixa cobertura de pesos — ausência
    de dado alarga a incerteza, nunca penaliza por imputação (mitiga viés).

    - ``subscores``: hazard → sub-score 0–100 (apenas os disponíveis).
    - ``weights``: hazard → peso (conjunto completo de hazards do modelo).
    - ``base_uncertainty``: meia-largura mínima da banda.
    - ``coverage_penalty``: meia-largura extra máxima quando cobertura = 0.

    Levanta ValueError se nenhum sub-score casar com os pesos.
    """
    present = {h: subscores[h] for h in subscores if h in weights}
    if not present:
        raise ValueError("nenhum sub-score corresponde aos pesos configurados")

    present_weight = sum(weights[h] for h in present)
    total_weight = sum(weights.values())
    coverage = present_weight / total_weight if total_weight else 0.0

    central = clamp(sum(weights[h] * s for h, s in present.items()) / present_weight, 0.0, 100.0)

    values = list(present.values())
    spread = (max(values) - min(values)) / 2.0 if len(values) > 1 else 0.0
    half_width = base_uncertainty + spread + (1.0 - coverage) * coverage_penalty

    return ScoreBand(
        central=central,
        low=clamp(central - half_width, 0.0, central),
        high=clamp(central + half_width, central, 100.0),
    )


def compose_score(
    physical: ScoreBand,
    transition: ScoreBand,
    *,
    weight_physical: float = 0.5,
    weight_transition: float = 0.5,
) -> ScoreBand:
    """Combinação linear de bandas. Implementação placeholder.

    A versão F1 vai considerar correlação entre pilares e propagação de
    incerteza não trivial. Por enquanto, soma ponderada conservadora.
    """
    if abs(weight_physical + weight_transition - 1.0) > 1e-6:
        raise ValueError("pesos devem somar 1.0")
    central = clamp(
        weight_physical * physical.central + weight_transition * transition.central, 0.0, 100.0
    )
    low = weight_physical * physical.low + weight_transition * transition.low
    high = weight_physical * physical.high + weight_transition * transition.high
    return ScoreBand(
        central=central,
        low=clamp(low, 0.0, central),
        high=clamp(high, central, 100.0),
    )
