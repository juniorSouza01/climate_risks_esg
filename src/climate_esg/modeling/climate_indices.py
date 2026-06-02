"""Indicadores climáticos a partir de dados regridded (Zarr da prata).

No F0 implementamos o mínimo para fechar o smoke test E2E: série mensal no
ponto de grade mais próximo de um ativo. Índices xclim ricos (Rx5day, TX90p,
WSDI, dias > 32 °C) entram na F1 (Épico 5 / climate_indices completo).

Funções recebem objetos xarray para manter a lógica desacoplada de I/O.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import xarray as xr

_LAT_NAMES = ("lat", "latitude", "rlat", "y", "nav_lat")
_LON_NAMES = ("lon", "longitude", "rlon", "x", "nav_lon")


def _coord_name(da: "xr.DataArray", candidates: tuple[str, ...]) -> str:
    for name in candidates:
        if name in da.coords or name in da.dims:
            return name
    raise ValueError(
        f"coordenada não encontrada entre {candidates} (coords={list(da.coords)})"
    )


def nearest_point_monthly(
    da: "xr.DataArray", lat: float, lon: float
) -> list[tuple[int, float]]:
    """Série mensal no ponto de grade mais próximo de (lat, lon).

    Retorna pares ``(date_sk, valor)`` onde ``date_sk = YYYYMM01`` (primeiro dia
    do mês — casa com ``dim_date``). Pressupõe dado de frequência mensal (Amon),
    um passo de tempo por mês. Valores NaN são descartados.
    """
    import math

    lat_name = _coord_name(da, _LAT_NAMES)
    lon_name = _coord_name(da, _LON_NAMES)
    point = da.sel({lat_name: lat, lon_name: lon}, method="nearest")

    # Reduz quaisquer dimensões além de 'time' (ex.: plev em 'hus') pela média,
    # garantindo um escalar por passo de tempo. Smoke-test-grade.
    extra_dims = [d for d in point.dims if d != "time"]
    if extra_dims:
        point = point.mean(dim=extra_dims)

    # O accessor .dt extrai ano/mês tanto de datetime64 (calendário padrão,
    # como sai do open_zarr) quanto de cftime (calendários CMIP6 não-padrão).
    time_coord = point["time"]
    years = time_coord.dt.year.values
    months = time_coord.dt.month.values
    values = point.values

    rows: list[tuple[int, float]] = []
    for year, month, raw in zip(years, months, values, strict=False):
        value = float(raw)
        if math.isnan(value):
            continue
        date_sk = int(year) * 10000 + int(month) * 100 + 1
        rows.append((date_sk, value))
    return rows
