from __future__ import annotations

from collections.abc import Sequence
from typing import Any

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


EXPECTED_UNITS: dict[str, tuple[str, ...]] = {
    "tas": ("K",),
    "tasmin": ("K",),
    "tasmax": ("K",),
    "pr": ("kg m-2 s-1", "kg/m2/s"),
    "prsn": ("kg m-2 s-1", "kg/m2/s"),
    "sfcWindmax": ("m s-1", "m/s"),
    "hurs": ("%",),
    "huss": ("1", "kg kg-1", "kg/kg"),
    "rsdt": ("W m-2", "W/m2"),
}

DEFAULT_MAX_NAN_FRACTION = 0.05


def check_units(variable: str, units: str | None) -> None:
    expected = EXPECTED_UNITS.get(variable)
    if expected is None:
        return
    if units is None or units.strip() not in expected:
        raise ValueError(
            f"{variable}: atributo units {units!r} difere do esperado {list(expected)}"
        )


def check_nan_fraction(
    variable: str, nan_fraction: float, *, max_nan_fraction: float = DEFAULT_MAX_NAN_FRACTION
) -> None:
    if not 0.0 <= nan_fraction <= 1.0:
        raise ValueError(f"{variable}: fração de NaN inválida ({nan_fraction!r})")
    if nan_fraction > max_nan_fraction:
        raise ValueError(
            f"{variable}: fração de NaN {nan_fraction:.4g} excede o máximo "
            f"permitido {max_nan_fraction:.4g}"
        )


def check_time_monotonic(time_values: Sequence[Any]) -> None:
    for i in range(1, len(time_values)):
        if not time_values[i] > time_values[i - 1]:
            raise ValueError(
                f"eixo tempo não estritamente crescente na posição {i} "
                f"({time_values[i - 1]!r} -> {time_values[i]!r})"
            )
