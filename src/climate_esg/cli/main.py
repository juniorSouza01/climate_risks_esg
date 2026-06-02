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

console = Console()


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
