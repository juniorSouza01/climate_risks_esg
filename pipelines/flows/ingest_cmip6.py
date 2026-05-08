"""Flow Prefect 3 — ingestão CMIP6 via wget scripts do MetaGrid ESGF.

Substitui a DAG Airflow prevista em `project.md` §7 (ver ADR-0003).

Tasks:
    fetch    — baixa o NetCDF para data/bronze, valida checksum.
    validate — abre com xarray/netCDF4 (a implementar na F1).
    promote  — regrid + recorte SC + Zarr na silver (a implementar na F1).
"""

from __future__ import annotations

from pathlib import Path

from prefect import flow, get_run_logger, task

from climate_esg.config import get_settings
from climate_esg.ingestion.esgf_client import (
    ESGFFile,
    download_manifest,
    parse_wget_script,
)
from climate_esg.utils.storage import cmip6_bronze_path, ensure_dir


@task(retries=2, retry_delay_seconds=30)
def fetch_manifest(wget_script: Path) -> list[Path]:
    """Lê o wget script e baixa todos os arquivos para bronze."""
    logger = get_run_logger()
    settings = get_settings()
    manifest = parse_wget_script(wget_script)
    logger.info("manifest %s: %d arquivos", wget_script.name, len(manifest))

    files = list(manifest.files)
    if not files:
        return []

    # Inferimos o destino bronze a partir do primeiro arquivo (todos do mesmo
    # dataset CMIP6 nos scripts gerados pelo MetaGrid).
    sample = next(f for f in files if f.cmip6 is not None)
    if sample.cmip6 is None:
        # Fallback: bronze raw bucket por nome de script.
        dest = ensure_dir(settings.data_bronze / "cmip6" / "_unparsed" / wget_script.stem)
    else:
        dest = ensure_dir(
            cmip6_bronze_path(
                source=sample.cmip6.source,
                experiment=sample.cmip6.experiment,
                member=sample.cmip6.member,
                table=sample.cmip6.table,
                variable=sample.cmip6.variable,
                grid=sample.cmip6.grid,
                version="vUNKNOWN",  # MetaGrid wget não preserva no nome; F1 lê do header NetCDF
            )
        )
    return download_manifest(manifest, dest, concurrency=4)


@task
def validate_netcdf(paths: list[Path]) -> list[Path]:
    """Abre cada NetCDF com xarray e checa metadados CF mínimos."""
    raise NotImplementedError("validate_netcdf: implementar na F1 com xarray + cf_xarray")


@task
def promote_to_silver(paths: list[Path]) -> list[Path]:
    """Regrid + recorte espacial SC + escrita Zarr na silver."""
    raise NotImplementedError("promote_to_silver: implementar na F1 com xarray + Dask + Zarr")


@flow(name="ingest-cmip6")
def ingest_cmip6_flow(
    wget_script: str | Path,
    *,
    do_validate: bool = False,
    do_promote: bool = False,
) -> list[Path]:
    """Pipeline completo de ingestão CMIP6 a partir de um wget script.

    Por padrão executa apenas a etapa fetch (smoke test do F0). validate e
    promote ficam atrás de flags até serem implementadas (F1).
    """
    paths = fetch_manifest(Path(wget_script))
    if do_validate:
        paths = validate_netcdf(paths)
    if do_promote:
        paths = promote_to_silver(paths)
    return paths
