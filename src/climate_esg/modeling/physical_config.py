"""Configuração metodológica do score de risco físico (externalizada do código).

project.md §12: o mapeamento metodológico fica em config, não no código, para
permitir recalibração sem redeploy. ADR-0005: hazards prioritários de Joinville/SC.

⚠️ Faixas de referência são CALIBRAÇÃO PROVISÓRIA (climatologia média da variável
em unidades nativas CMIP6). Na F1 madura serão substituídas por índices xclim
(Rx5day, TX90p, WSDI…) com faixas calibradas por literatura/NGFS.
"""

from __future__ import annotations

from dataclasses import dataclass

# Pesos por hazard (somam 1.0). ADR-0005: enchente e calor dominam em SC.
HAZARD_WEIGHTS: dict[str, float] = {
    "enchente": 0.35,
    "calor": 0.25,
    "vento": 0.20,
    "deslizamento": 0.20,
}


@dataclass(frozen=True, slots=True)
class IndicatorReference:
    """Como uma variável CF vira sub-score de hazard.

    ``ref_low`` → 0 e ``ref_high`` → 100 na normalização linear. ``ref_low`` >
    ``ref_high`` inverte (menor = pior). Valores na unidade nativa do CMIP6.
    """

    hazard: str
    ref_low: float
    ref_high: float


# Variável CF (climatologia média) → referência de normalização.
# rsdt/hurs/huss/hus/prsn não mapeiam a hazard prioritário no MVP (ignorados).
INDICATOR_REFERENCE: dict[str, IndicatorReference] = {
    # precipitação média (kg m-2 s-1): mais chuva → mais risco de enchente.
    "pr": IndicatorReference(hazard="enchente", ref_low=0.0, ref_high=1.0e-4),
    # temp. máxima média (K): 25 °C → 0, 40 °C → 100 (calor extremo).
    "tasmax": IndicatorReference(hazard="calor", ref_low=298.15, ref_high=313.15),
    # temp. mínima média (K): noites quentes como proxy de calor (10 → 25 °C).
    "tasmin": IndicatorReference(hazard="calor", ref_low=283.15, ref_high=298.15),
    # vento máximo médio (m s-1): 0 → 25 m/s.
    "sfcWindmax": IndicatorReference(hazard="vento", ref_low=0.0, ref_high=25.0),
}

PHYSICAL_MODEL_NAME = "physical_weighted_sum"
PHYSICAL_MODEL_VERSION = "0.1.0"
