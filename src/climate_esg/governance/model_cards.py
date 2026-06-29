from __future__ import annotations

import datetime as dt
import json
from typing import Any

_USAGE = (
    "## Uso e limitações\n"
    "- Score destinado a triagem de risco climático (TCFD/ISSB S2); **não** usar isolado "
    "para decisão fiduciária.\n"
    "- MVP: indicadores físicos por climatologia média; cenários SSP e índices xclim em evolução.\n"
    "- Inputs de transição curados (placeholder até ingestão CDP/CVM).\n"
    "- Banda de incerteza reflete cobertura de dados; baixa cobertura alarga a banda.\n"
)


def build_model_card(
    *,
    run_sk: int,
    model_name: str,
    model_version: str,
    code_commit: str | None,
    train_data_version: str | None,
    hyperparams: dict[str, Any] | None,
    created_at: dt.datetime | None,
) -> str:
    params = json.dumps(hyperparams or {}, ensure_ascii=False, indent=2)
    created = created_at.isoformat() if created_at is not None else "—"
    return (
        f"# Model Card — {model_name} v{model_version}\n\n"
        f"- **run_sk:** {run_sk}\n"
        f"- **commit:** {code_commit or '—'}\n"
        f"- **versão dos dados:** {train_data_version or '—'}\n"
        f"- **criado em:** {created}\n\n"
        f"## Hiperparâmetros\n```json\n{params}\n```\n\n"
        f"{_USAGE}"
    )
