from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from prefect import flow, get_run_logger, task

from climate_esg.config import get_settings
from climate_esg.db.base import session_scope
from climate_esg.db.models import (
    DimAsset,
    DimClimateVariable,
    DimDate,
    DimScenario,
    FactClimateIndicator,
)
from climate_esg.geospatial.regions import SANTA_CATARINA, BBox
from climate_esg.governance.lineage import hash_data_version, start_model_run
from climate_esg.ingestion.cf_validation import check_value_range
from climate_esg.ingestion.esgf_client import (
    CMIP6Identifier,
    download_manifest,
    parse_wget_script,
)
from climate_esg.ingestion.netcdf_loader import (
    main_data_var,
    open_mfnetcdf,
    open_netcdf,
)
from climate_esg.modeling.climate_indices import nearest_point_monthly
from climate_esg.utils.storage import cmip6_bronze_path, cmip6_silver_path, ensure_dir

if TYPE_CHECKING:
    import xarray as xr

# Experimento CMIP6 -> nome do cenário em dim_scenario (seed.py).
_EXPERIMENT_TO_SCENARIO = {
    "historical": "historical",
    "ssp245": "SSP2-4.5",
    "ssp585": "SSP5-8.5",
}

_LAT_NAMES = ("lat", "latitude", "rlat", "y", "nav_lat")
_LON_NAMES = ("lon", "longitude", "rlon", "x", "nav_lon")

MODEL_NAME = "cmip6_ingest"
MODEL_VERSION = "0.1.0"


# ---------------------------------------------------------------------------
# fetch
# ---------------------------------------------------------------------------


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

    sample = next((f for f in files if f.cmip6 is not None), None)
    if sample is None or sample.cmip6 is None:
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
                version="vUNKNOWN",  # MetaGrid wget não preserva; F1 lê do header NetCDF
            )
        )
    return download_manifest(manifest, dest, concurrency=4)


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


@task
def validate_netcdf(paths: list[Path]) -> list[Path]:
    """Abre cada NetCDF, acha a variável de dado e checa faixa física plausível."""
    logger = get_run_logger()
    validated: list[Path] = []
    for p in paths:
        ident = CMIP6Identifier.from_filename(p.name)
        expected = ident.variable if ident else None
        ds = open_netcdf(p)
        try:
            var_name = main_data_var(ds, expected=expected)
            da = ds[var_name]
            if "time" not in da.dims:
                raise ValueError(f"{p.name}: variável {var_name} sem dimensão 'time'")
            vmin = float(da.min().compute())
            vmax = float(da.max().compute())
            check_value_range(var_name, vmin, vmax)
            logger.info("validate ok: %s (%s ∈ [%.4g, %.4g])", p.name, var_name, vmin, vmax)
        finally:
            ds.close()
        validated.append(p)
    return validated


# ---------------------------------------------------------------------------
# promote
# ---------------------------------------------------------------------------


def _coord_name(ds: xr.Dataset, candidates: tuple[str, ...]) -> str:
    for name in candidates:
        if name in ds.coords or name in ds.dims:
            return name
    raise ValueError(f"coordenada não encontrada entre {candidates}")


def _normalize_longitudes(ds: xr.Dataset) -> xr.Dataset:
    """Converte longitudes 0..360 para -180..180 e reordena, se necessário."""
    lon_name = _coord_name(ds, _LON_NAMES)
    if float(ds[lon_name].max()) > 180.0:
        ds = ds.assign_coords({lon_name: (((ds[lon_name] + 180) % 360) - 180)})
        ds = ds.sortby(lon_name)
    return ds


def _crop_bbox(ds: xr.Dataset, bbox: BBox) -> xr.Dataset:
    """Recorta o dataset ao bounding box (lida com latitude asc/desc)."""
    lat_name = _coord_name(ds, _LAT_NAMES)
    lon_name = _coord_name(ds, _LON_NAMES)
    lat_vals = ds[lat_name].values
    if len(lat_vals) > 1 and lat_vals[0] > lat_vals[-1]:
        lat_slice = slice(bbox.lat_max, bbox.lat_min)
    else:
        lat_slice = slice(bbox.lat_min, bbox.lat_max)
    return ds.sel({lat_name: lat_slice, lon_name: slice(bbox.lon_min, bbox.lon_max)})


@task
def promote_to_silver(paths: list[Path]) -> list[dict[str, str]]:
    """Agrupa por dataset CMIP6, concatena no tempo, recorta SC e grava Zarr.

    Cada dataset (mesmo source/experiment/member/table/variable/grid, diferindo
    só no período anual) vira UM Zarr contínuo no tempo — não um arquivo
    sobrescrevendo o outro. Regridding p/ grade comum (xesmf) fica para a F1;
    no F0 preservamos a grade nativa recortada.
    """
    logger = get_run_logger()

    # Agrupa os arquivos anuais por dataset (ignorando o período).
    groups: dict[tuple[str, ...], list[Path]] = {}
    idents: dict[tuple[str, ...], CMIP6Identifier] = {}
    for p in paths:
        ident = CMIP6Identifier.from_filename(p.name)
        if ident is None:
            logger.warning("promote: nome fora do padrão CMIP6, pulando: %s", p.name)
            continue
        key = (
            ident.source,
            ident.experiment,
            ident.member,
            ident.table,
            ident.variable,
            ident.grid,
        )
        groups.setdefault(key, []).append(p)
        idents[key] = ident

    promoted: list[dict[str, str]] = []
    for key, group_paths in groups.items():
        ident = idents[key]
        ds = open_mfnetcdf(group_paths)
        try:
            ds = _normalize_longitudes(ds)
            ds = _crop_bbox(ds, SANTA_CATARINA)
            store = cmip6_silver_path(
                source=ident.source,
                experiment=ident.experiment,
                member=ident.member,
                table=ident.table,
                variable=ident.variable,
                grid=ident.grid,
            )
            ensure_dir(store.parent)
            ds.to_zarr(store, mode="w", consolidated=False)
            logger.info("promote ok: %d arquivos -> %s", len(group_paths), store)
        finally:
            ds.close()
        promoted.append(
            {
                "store": str(store),
                "source": ident.source,
                "experiment": ident.experiment,
                "member": ident.member,
                "table": ident.table,
                "variable": ident.variable,
                "grid": ident.grid,
            }
        )
    return promoted


# ---------------------------------------------------------------------------
# materialize (ouro)
# ---------------------------------------------------------------------------


@task
def materialize_indicators(promoted: list[dict[str, str]]) -> int:
    """Série mensal por ativo → fact_climate_indicator, com run_sk (linhagem).

    Para cada dataset promovido: para cada ativo seeded, extrai a série mensal
    no ponto de grade mais próximo e grava como value_mean. Smoke-test-grade —
    agregações espaciais e índices xclim entram na F1.
    """
    import xarray as xr

    logger = get_run_logger()
    if not promoted:
        return 0

    stores = [d["store"] for d in promoted]
    rows_written = 0
    dropped_out_of_calendar = 0

    with session_scope() as session:
        run_sk = start_model_run(
            session,
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            hyperparams={"bbox": "santa_catarina", "agg": "nearest_point_monthly"},
            train_data_version=hash_data_version(stores),
        )

        assets = session.scalars(sa.select(DimAsset).order_by(DimAsset.asset_sk)).all()
        valid_date_sks = set(session.scalars(sa.select(DimDate.date_sk)).all())

        for meta in promoted:
            scenario_name = _EXPERIMENT_TO_SCENARIO.get(meta["experiment"])
            scenario_sk = session.scalar(
                sa.select(DimScenario.scenario_sk).where(DimScenario.name == scenario_name)
            )
            var_sk = session.scalar(
                sa.select(DimClimateVariable.var_sk).where(
                    DimClimateVariable.cf_code == meta["variable"]
                )
            )
            if scenario_sk is None or var_sk is None:
                logger.warning(
                    "materialize: faltam chaves (exp=%s var=%s) — rode o seed; pulando",
                    meta["experiment"],
                    meta["variable"],
                )
                continue

            ds = xr.open_zarr(meta["store"], consolidated=False)
            try:
                da = ds[main_data_var(ds, expected=meta["variable"])]
                for asset in assets:
                    if asset.latitude is None or asset.longitude is None:
                        continue
                    series = nearest_point_monthly(
                        da, float(asset.latitude), float(asset.longitude)
                    )
                    for date_sk, value in series:
                        if date_sk not in valid_date_sks:
                            dropped_out_of_calendar += 1
                            continue  # fora do calendário seeded (dim_date)
                        session.add(
                            FactClimateIndicator(
                                asset_sk=asset.asset_sk,
                                var_sk=var_sk,
                                scenario_sk=scenario_sk,
                                date_sk=date_sk,
                                run_sk=run_sk,
                                value_mean=value,
                            )
                        )
                        rows_written += 1
            finally:
                ds.close()

    if dropped_out_of_calendar:
        logger.warning(
            "materialize: %d pontos ignorados por estarem fora do calendário "
            "dim_date — rode `make db-seed` para cobrir o período",
            dropped_out_of_calendar,
        )
    logger.info(
        "materialize: %d linhas em fact_climate_indicator (run_sk=%s)", rows_written, run_sk
    )
    return rows_written


# ---------------------------------------------------------------------------
# flow
# ---------------------------------------------------------------------------


@flow(name="ingest-cmip6")
def ingest_cmip6_flow(
    wget_script: str | Path,
    *,
    do_validate: bool = False,
    do_promote: bool = False,
    do_materialize: bool = False,
) -> dict[str, Any]:
    """Pipeline de ingestão CMIP6 a partir de um wget script.

    Por padrão executa só o fetch (smoke do F0 inicial). As etapas seguintes
    ficam atrás de flags e dependem da anterior.
    """
    paths = fetch_manifest(Path(wget_script))
    result: dict[str, Any] = {"fetched": len(paths)}

    if do_validate:
        paths = validate_netcdf(paths)
        result["validated"] = len(paths)

    if do_promote:
        promoted = promote_to_silver(paths)
        result["promoted"] = len(promoted)
        if do_materialize:
            result["indicator_rows"] = materialize_indicators(promoted)

    return result
