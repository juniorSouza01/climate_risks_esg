"""Abstração mínima sobre o data lake local.

ADR-0002: o object store MinIO foi substituído pelo filesystem local. Este
módulo encapsula o layout para que pontos de uso não dependam de paths
absolutos. Migrar para S3/MinIO no futuro só altera este arquivo.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from climate_esg.config import get_settings


class Layer(StrEnum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


def layer_root(layer: Layer) -> Path:
    """Path absoluto da raiz de uma camada do data lake."""
    s = get_settings()
    match layer:
        case Layer.BRONZE:
            return s.data_bronze
        case Layer.SILVER:
            return s.data_silver
        case Layer.GOLD:
            return s.data_gold


def cmip6_bronze_path(
    *,
    source: str,
    experiment: str,
    member: str,
    table: str,
    variable: str,
    grid: str,
    version: str,
) -> Path:
    """Layout DRS para CMIP6 bronze (project.md §6.3).

    Ex.: data/bronze/cmip6/EC-Earth3/historical/r120i1p1f1/Amon/tasmin/gr/v20200412/
    """
    return (
        layer_root(Layer.BRONZE)
        / "cmip6"
        / source
        / experiment
        / member
        / table
        / variable
        / grid
        / version
    )


def cmip6_silver_path(
    *,
    source: str,
    experiment: str,
    member: str,
    table: str,
    variable: str,
    grid: str,
) -> Path:
    """Store Zarr da camada prata para um dataset CMIP6 (já regridded/recortado).

    Ex.: data/silver/cmip6/EC-Earth3/historical/r120i1p1f1/Amon/tasmin/gr.zarr
    """
    return (
        layer_root(Layer.SILVER)
        / "cmip6"
        / source
        / experiment
        / member
        / table
        / variable
        / f"{grid}.zarr"
    )


def ensure_dir(path: Path) -> Path:
    """mkdir -p; retorna o próprio path para uso em chains."""
    path.mkdir(parents=True, exist_ok=True)
    return path
