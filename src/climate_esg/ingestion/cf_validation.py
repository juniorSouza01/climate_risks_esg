from __future__ import annotations

# Faixas em UNIDADES NATIVAS do CMIP6 (temperatura em Kelvin, pr em kg m-2 s-1).
# Variável CF -> (mínimo plausível, máximo plausível).
PLAUSIBLE_RANGES: dict[str, tuple[float, float]] = {
    "tas": (173.15, 333.15),  # -100 .. 60 °C
    "tasmin": (173.15, 333.15),
    "tasmax": (173.15, 333.15),
    "pr": (0.0, 0.02),  # ~0 .. 1728 mm/dia (folga p/ extremos)
    "prsn": (0.0, 0.02),
    "sfcWindmax": (0.0, 150.0),  # m/s
    "hurs": (0.0, 100.0),  # %
    "huss": (0.0, 0.1),  # kg/kg
    "rsdt": (0.0, 600.0),  # W/m²
}


def check_value_range(variable: str, observed_min: float, observed_max: float) -> None:

    rng = PLAUSIBLE_RANGES.get(variable)
    if rng is None:
        return
    lo, hi = rng
    if observed_min < lo or observed_max > hi:
        raise ValueError(
            f"{variable}: faixa observada [{observed_min:.4g}, {observed_max:.4g}] "
            f"fora do plausível [{lo:.4g}, {hi:.4g}]"
        )
