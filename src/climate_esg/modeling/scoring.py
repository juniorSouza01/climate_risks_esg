"""Composição final de score (placeholder).

A implementação real entra na F1. Este módulo serve para ancorar os tipos
e o contrato (entrada/saída) que outras camadas (api, governance) podem
referenciar desde já.
"""

from __future__ import annotations

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
    return ScoreBand(
        central=weight_physical * physical.central + weight_transition * transition.central,
        low=weight_physical * physical.low + weight_transition * transition.low,
        high=weight_physical * physical.high + weight_transition * transition.high,
    )
