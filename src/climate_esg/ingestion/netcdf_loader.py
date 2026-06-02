from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import xarray as xr


def _time_coder() -> "xr.coders.CFDatetimeCoder":
    """Coder de tempo CF (substitui o kwarg ``use_cftime``, hoje deprecado)."""
    import xarray as xr

    return xr.coders.CFDatetimeCoder(use_cftime=True)

# Coordenadas/variáveis auxiliares que NÃO são a variável de dado de interesse.
_AUX_NAMES = {
    "time",
    "time_bnds",
    "time_bounds",
    "lat",
    "latitude",
    "lat_bnds",
    "lon",
    "longitude",
    "lon_bnds",
    "bnds",
    "height",
    "depth",
    "lev",
    "plev",
    "type",
}


def open_netcdf(path: str | Path, *, chunks: str | dict[str, int] | None = "auto") -> "xr.Dataset":

    import xarray as xr

    return xr.open_dataset(path, decode_times=_time_coder(), chunks=chunks)


def open_mfnetcdf(
    paths: Iterable[str | Path], *, chunks: str | dict[str, int] | None = "auto"
) -> "xr.Dataset":

    import xarray as xr

    files = sorted(str(p) for p in paths)
    # data_vars/coords="minimal" + compat="override": receita canônica para
    # concatenar arquivos anuais CMIP6 da MESMA variável ao longo do tempo,
    # sem broadcast de variáveis auxiliares (e silencia o FutureWarning).
    return xr.open_mfdataset(
        files,
        combine="by_coords",
        decode_times=_time_coder(),
        chunks=chunks,
        data_vars="minimal",
        coords="minimal",
        compat="override",
    )


def main_data_var(ds: "xr.Dataset", *, expected: str | None = None) -> str:
    """Descobre o nome da variável de dado principal do dataset.

    Se ``expected`` for passado (ex.: derivado do nome do arquivo CMIP6) e
    existir no dataset, ele tem prioridade. Caso contrário, escolhe a primeira
    variável que não seja coordenada/auxiliar.

    Levanta ValueError se não houver variável de dado plausível.
    """
    if expected and expected in ds.data_vars:
        return expected

    for name in ds.data_vars:
        if str(name) not in _AUX_NAMES:
            return str(name)

    raise ValueError(
        f"nenhuma variável de dado encontrada no dataset (data_vars={list(ds.data_vars)})"
    )
