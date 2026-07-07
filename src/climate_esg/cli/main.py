"""CLI ``climate-esg`` instalado via [project.scripts] do pyproject.

No F0 cobre apenas operações de inspeção dos manifests ESGF e bootstrap.
Pipelines reais ficam em ``pipelines/flows/`` (Prefect 3).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import typer
from rich.console import Console
from rich.table import Table

from climate_esg.ingestion.esgf_client import (
    parse_wget_directory,
    parse_wget_script,
)
from climate_esg.logging import configure_logging

app = typer.Typer(no_args_is_help=True, add_completion=False)
manifests_app = typer.Typer(help="Inspeção de manifests ESGF.")
app.add_typer(manifests_app, name="manifests")
db_app = typer.Typer(help="Operações de banco (seed, etc.).")
app.add_typer(db_app, name="db")
geo_app = typer.Typer(help="Geocodificação de ativos (BrasilAPI + Nominatim).")
app.add_typer(geo_app, name="geo")
ingest_app = typer.Typer(help="Ingestão de fontes corporativas.")
app.add_typer(ingest_app, name="ingest")

console = Console()


@ingest_app.command("b3-universe", help="Ingere empresas da B3 (brapi) em dim_company.")
def ingest_b3_universe_cmd(
    target: int = typer.Option(200, help="Quantas empresas buscar (paginado)."),
) -> None:
    configure_logging()
    from climate_esg.db.base import session_scope
    from climate_esg.ingestion.b3_universe import ingest_b3_universe

    with session_scope() as session:
        added = ingest_b3_universe(session, target)
    console.print(f"[bold green]{added} empresas adicionadas ao universo B3.[/bold green]")


@ingest_app.command("cvm-financials", help="Ingere receita/lucro do DFP da CVM e casa por nome.")
def ingest_cvm_financials_cmd(
    year: int = typer.Option(..., help="Ano fiscal do DFP (ex.: 2023)."),
) -> None:
    configure_logging()
    from climate_esg.db.base import session_scope
    from climate_esg.ingestion.cvm import ingest_cvm_financials

    with session_scope() as session:
        matched = ingest_cvm_financials(session, year)
    console.print(f"[bold green]{matched} empresas com financeiro CVM {year}.[/bold green]")


@ingest_app.command(
    "adaptabrasil", help="Ingere risco municipal (enchente/deslizamento) do AdaptaBrasil."
)
def ingest_adaptabrasil_cmd() -> None:
    configure_logging()
    from climate_esg.db.base import session_scope
    from climate_esg.ingestion.adaptabrasil import ingest_adaptabrasil_exposure

    with session_scope() as session:
        written = ingest_adaptabrasil_exposure(session)
    console.print(f"[bold green]{written} exposições AdaptaBrasil gravadas.[/bold green]")


@geo_app.command("locate", help="Geocodifica uma consulta livre via Nominatim/OSM.")
def geo_locate(
    query: str = typer.Argument(..., help="Ex.: 'Joinville, SC, Brasil'"),
) -> None:
    configure_logging()
    from climate_esg.ingestion.geocoding import geocode

    result = geocode(query)
    if result is None:
        console.print("[yellow]Sem resultado.[/yellow]")
        raise typer.Exit(1)
    console.print(f"{result.latitude}, {result.longitude} — {result.display_name}")


@geo_app.command("cnpj", help="Geocodifica uma empresa pelo CNPJ (BrasilAPI → Nominatim).")
def geo_cnpj(cnpj: str = typer.Argument(..., help="CNPJ com ou sem máscara")) -> None:
    configure_logging()
    from climate_esg.ingestion.geocoding import geocode_cnpj

    result = geocode_cnpj(cnpj)
    if result is None:
        console.print("[yellow]CNPJ não encontrado ou sem geocodificação.[/yellow]")
        raise typer.Exit(1)
    console.print(f"{result.latitude}, {result.longitude} — {result.display_name}")


@geo_app.command("refresh-assets", help="Atualiza lat/long/geom dos ativos via município.")
def geo_refresh_assets() -> None:
    configure_logging()
    import sqlalchemy as sa
    from geoalchemy2.elements import WKTElement

    from climate_esg.db.base import session_scope
    from climate_esg.db.models import DimAsset
    from climate_esg.ingestion.geocoding import build_address_query, geocode

    updated = 0
    with session_scope() as session:
        rows = session.execute(
            sa.select(DimAsset.asset_sk, DimAsset.name, DimAsset.municipality, DimAsset.state)
        ).all()
        for asset_sk, name, municipality, state in rows:
            if not municipality:
                continue
            result = geocode(build_address_query(municipality=municipality, state=state))
            if result is None:
                continue
            session.execute(
                sa.update(DimAsset)
                .where(DimAsset.asset_sk == asset_sk)
                .values(
                    latitude=result.latitude,
                    longitude=result.longitude,
                    geom=WKTElement(f"POINT({result.longitude} {result.latitude})", srid=4326),
                )
            )
            updated += 1
            console.print(f"[green]{name}[/green] → {result.latitude:.4f}, {result.longitude:.4f}")
    console.print(f"[bold]{updated} ativos atualizados.[/bold]")


@geo_app.command(
    "resolve-ibge", help="Preenche dim_asset.ibge_code via API do IBGE (município+UF)."
)
def geo_resolve_ibge() -> None:
    configure_logging()
    import sqlalchemy as sa

    from climate_esg.db.base import session_scope
    from climate_esg.db.models import DimAsset
    from climate_esg.ingestion.ibge import resolve_ibge_code

    updated = 0
    with session_scope() as session:
        rows = session.execute(
            sa.select(DimAsset.asset_sk, DimAsset.municipality, DimAsset.state)
        ).all()
        for asset_sk, municipality, state in rows:
            if not municipality or not state:
                continue
            code = resolve_ibge_code(municipality, state)
            if code is None:
                continue
            session.execute(
                sa.update(DimAsset).where(DimAsset.asset_sk == asset_sk).values(ibge_code=code)
            )
            updated += 1
            console.print(f"[green]{municipality}/{state}[/green] → IBGE {code}")
    console.print(f"[bold]{updated} ativos com IBGE resolvido.[/bold]")


@db_app.command(
    "prune-dossier-cache", help="Remove entradas expiradas do cache do dossiê (cache_dossier)."
)
def db_prune_dossier_cache() -> None:
    configure_logging()
    import datetime as dt

    import sqlalchemy as sa

    from climate_esg.db.base import session_scope
    from climate_esg.db.models import CacheDossier

    now = dt.datetime.now(dt.UTC)
    with session_scope() as session:
        result = cast(
            "sa.CursorResult[Any]",
            session.execute(sa.delete(CacheDossier).where(CacheDossier.expires_at <= now)),
        )
        removed = result.rowcount or 0
    console.print(
        f"[bold green]{removed} entradas expiradas removidas do cache do dossiê.[/bold green]"
    )


@db_app.command(
    "prune-model-runs",
    help="Remove runs órfãos (sem fatos) não-success antigos de dim_model_run.",
)
def db_prune_model_runs(
    days: int = typer.Option(30, help="Idade mínima (dias) do run para remoção."),
) -> None:
    configure_logging()
    import datetime as dt

    import sqlalchemy as sa

    from climate_esg.db.base import session_scope
    from climate_esg.db.models import (
        DimModelRun,
        FactClimateIndicator,
        FactFinancialImpact,
        FactHazardExposure,
        FactPhysicalRiskScore,
        FactScoreExplanation,
        FactTransitionRiskScore,
    )

    cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(days=days)
    fact_tables = (
        FactClimateIndicator,
        FactPhysicalRiskScore,
        FactTransitionRiskScore,
        FactFinancialImpact,
        FactHazardExposure,
        FactScoreExplanation,
    )
    conditions = [
        DimModelRun.status != "success",
        DimModelRun.created_at < cutoff,
    ]
    for fact in fact_tables:
        conditions.append(
            ~sa.exists(sa.select(fact.run_sk).where(fact.run_sk == DimModelRun.run_sk))
        )
    with session_scope() as session:
        result = cast(
            "sa.CursorResult[Any]",
            session.execute(sa.delete(DimModelRun).where(*conditions)),
        )
        removed = result.rowcount or 0
    console.print(
        f"[bold green]{removed} runs órfãos/failed (>{days}d) removidos de dim_model_run.[/bold green]"
    )


@db_app.command("seed")
def db_seed() -> None:
    """Popula as dimensões-base do MVP (idempotente)."""
    configure_logging()
    from climate_esg.db.seed import run

    run()
    console.print("[bold green]Seed concluído.[/bold green]")


@manifests_app.command("inspect")
def manifests_inspect(
    path: Path = typer.Argument(..., exists=True, help="Arquivo .sh ou diretório"),
) -> None:
    """Sumariza um wget script (ou diretório com vários)."""
    configure_logging()
    manifests = [parse_wget_script(path)] if path.is_file() else parse_wget_directory(path)

    table = Table(title="ESGF manifests")
    table.add_column("script", style="cyan", no_wrap=True)
    table.add_column("# files", justify="right")
    table.add_column("variables")
    table.add_column("members")
    table.add_column("experiments")

    total = 0
    for m in manifests:
        table.add_row(
            m.source_path.name,
            str(len(m)),
            ", ".join(sorted(m.variables())) or "—",
            ", ".join(sorted(m.members())) or "—",
            ", ".join(sorted(m.experiments())) or "—",
        )
        total += len(m)

    console.print(table)
    console.print(f"[bold]Total de arquivos catalogados:[/bold] {total}")


@app.callback()
def _root() -> None:
    """climate-esg — CLI de operações da plataforma."""
