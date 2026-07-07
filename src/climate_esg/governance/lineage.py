from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy.orm import Session

from climate_esg.config import REPO_ROOT, get_settings
from climate_esg.db.models import (
    DimModelRun,
    FactClimateIndicator,
    FactFinancialImpact,
    FactHazardExposure,
    FactPhysicalRiskScore,
    FactScoreExplanation,
    FactTransitionRiskScore,
)
from climate_esg.logging import get_logger

log = get_logger(__name__)

_RUN_LINKED_FACTS = (
    FactClimateIndicator,
    FactPhysicalRiskScore,
    FactTransitionRiskScore,
    FactFinancialImpact,
    FactHazardExposure,
    FactScoreExplanation,
)


def current_git_commit(repo_root: Path | None = None) -> str | None:
    """SHA do commit atual (HEAD). Retorna None se git indisponível/sem repo."""
    root = repo_root or REPO_ROOT
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError):
        return None
    if result.returncode != 0:
        return None
    commit = result.stdout.strip()
    return commit or None


def hash_data_version(items: Iterable[str], *, length: int = 16) -> str:

    payload = json.dumps(sorted(items), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:length]


def _log_mlflow(
    run_sk: int,
    model_name: str,
    model_version: str,
    hyperparams: dict[str, Any] | None,
) -> None:
    try:
        import os

        os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
        import mlflow

        mlflow.set_tracking_uri(get_settings().mlflow_tracking_uri)
        mlflow.set_experiment("climate-esg")
        with mlflow.start_run(run_name=f"{model_name}-{run_sk}"):
            mlflow.set_tag("run_sk", str(run_sk))
            mlflow.log_param("model_name", model_name)
            mlflow.log_param("model_version", model_version)
            for key, value in (hyperparams or {}).items():
                mlflow.log_param(key, value)
    except Exception as exc:
        log.warning("mlflow.log.failed", run_sk=run_sk, error=str(exc))


def start_model_run(
    session: Session,
    *,
    model_name: str,
    model_version: str,
    hyperparams: dict[str, Any] | None = None,
    train_data_version: str | None = None,
    code_commit: str | None = None,
) -> int:

    run = DimModelRun(
        model_name=model_name,
        model_version=model_version,
        code_commit=code_commit if code_commit is not None else current_git_commit(),
        train_data_version=train_data_version,
        hyperparams=hyperparams,
        status="running",
    )
    session.add(run)
    session.flush()  # popula run.run_sk (IDENTITY) sem fechar a transação
    _log_mlflow(run.run_sk, model_name, model_version, hyperparams)
    return run.run_sk


def prune_stale_runs(
    session: Session,
    *,
    older_than_days: int = 30,
    statuses: tuple[str, ...] = ("failed", "empty"),
) -> int:
    cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(days=older_than_days)
    run_sks = list(
        session.scalars(
            sa.select(DimModelRun.run_sk).where(
                DimModelRun.status.in_(statuses),
                sa.func.coalesce(DimModelRun.finished_at, DimModelRun.created_at) < cutoff,
            )
        ).all()
    )
    if not run_sks:
        return 0
    facts_deleted = 0
    for fact in _RUN_LINKED_FACTS:
        result = cast(
            "sa.CursorResult[Any]",
            session.execute(sa.delete(fact).where(fact.run_sk.in_(run_sks))),
        )
        facts_deleted += result.rowcount or 0
    session.execute(sa.delete(DimModelRun).where(DimModelRun.run_sk.in_(run_sks)))
    session.flush()
    log.info(
        "lineage.prune_stale_runs",
        runs_deleted=len(run_sks),
        facts_deleted=facts_deleted,
        older_than_days=older_than_days,
        statuses=list(statuses),
    )
    return len(run_sks)


def finish_model_run(session: Session, run_sk: int, status: str) -> None:
    run = session.get(DimModelRun, run_sk)
    if run is None:
        log.warning("finish_model_run.missing", run_sk=run_sk, status=status)
        return
    run.status = status
    run.finished_at = dt.datetime.now(dt.UTC)
    session.flush()
