from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from climate_esg.config import REPO_ROOT
from climate_esg.db.models import DimModelRun


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
    )
    session.add(run)
    session.flush()  # popula run.run_sk (IDENTITY) sem fechar a transação
    return run.run_sk
