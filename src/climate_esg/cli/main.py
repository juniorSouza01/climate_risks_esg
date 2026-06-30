"""CLI ``climate-esg`` instalado via [project.scripts] do pyproject.

No F0 cobre apenas operações de inspeção dos manifests ESGF e bootstrap.
Pipelines reais ficam em ``pipelines/flows/`` (Prefect 3).
"""

from __future__ import annotations

from pathlib import Path

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
