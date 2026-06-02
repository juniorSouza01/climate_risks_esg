"""Flow Prefect 3 — cálculo de scores a partir da camada ouro.

No MVP cobre o score físico (soma ponderada de indicadores normalizados,
project.md §8). Lê ``fact_climate_indicator`` e grava ``fact_physical_risk_score``
com ``run_sk`` (linhagem §2.2.2). Transição (ADR-0004) entra na F2.

⚠️ MVP-grade: indicador = climatologia média da variável. Scores significativos
dependem das variáveis de hazard (pr/tasmax/sfcWindmax) e cenários SSP, ainda a
ingerir (ADR-0005). Com apenas ``historical``/``rsdt`` a maioria das empresas é
pulada por falta de variável mapeável.
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from prefect import flow, get_run_logger, task

from climate_esg.db.base import session_scope
from climate_esg.db.models import (
    DimAsset,
    DimClimateVariable,
    DimScenario,
    FactClimateIndicator,
    FactPhysicalRiskScore,
)
from climate_esg.governance.lineage import start_model_run
from climate_esg.modeling.physical_config import (
    HAZARD_WEIGHTS,
    PHYSICAL_MODEL_NAME,
    PHYSICAL_MODEL_VERSION,
)
from climate_esg.modeling.physical_risk import compute_physical_score


@task
def score_physical(scenario_name: str, horizon_year: int) -> int:
    """Calcula e grava o score físico de cada empresa para um cenário/horizonte.

    Retorna o número de empresas pontuadas. Empresas sem variável de hazard
    mapeável são puladas (logadas), não recebem score imputado.
    """
    logger = get_run_logger()
    scored = 0

    with session_scope() as session:
        scenario_sk = session.scalar(
            sa.select(DimScenario.scenario_sk).where(DimScenario.name == scenario_name)
        )
        if scenario_sk is None:
            logger.warning("score_physical: cenário '%s' não existe — rode o seed", scenario_name)
            return 0

        run_sk = start_model_run(
            session,
            model_name=PHYSICAL_MODEL_NAME,
            model_version=PHYSICAL_MODEL_VERSION,
            hyperparams={"weights": HAZARD_WEIGHTS, "horizon_year": horizon_year},
        )

        # Climatologia média por (empresa, variável CF) no cenário.
        mean_rows = session.execute(
            sa.select(
                DimAsset.company_sk,
                DimClimateVariable.cf_code,
                sa.func.avg(FactClimateIndicator.value_mean),
            )
            .join(DimAsset, DimAsset.asset_sk == FactClimateIndicator.asset_sk)
            .join(
                DimClimateVariable,
                DimClimateVariable.var_sk == FactClimateIndicator.var_sk,
            )
            .where(FactClimateIndicator.scenario_sk == scenario_sk)
            .group_by(DimAsset.company_sk, DimClimateVariable.cf_code)
        ).all()

        # Nº de ativos com dado por empresa.
        asset_counts = dict(
            session.execute(
                sa.select(
                    DimAsset.company_sk,
                    sa.func.count(sa.distinct(FactClimateIndicator.asset_sk)),
                )
                .join(DimAsset, DimAsset.asset_sk == FactClimateIndicator.asset_sk)
                .where(FactClimateIndicator.scenario_sk == scenario_sk)
                .group_by(DimAsset.company_sk)
            ).all()
        )

        var_means: dict[int, dict[str, float]] = {}
        for company_sk, cf_code, avg_value in mean_rows:
            if avg_value is None:
                continue
            var_means.setdefault(company_sk, {})[cf_code] = float(avg_value)

        for company_sk, means in var_means.items():
            try:
                result = compute_physical_score(means)
            except ValueError:
                logger.warning(
                    "score_physical: empresa %s sem variável de hazard mapeável "
                    "(vars=%s) — pulando",
                    company_sk,
                    sorted(means),
                )
                continue

            session.add(
                FactPhysicalRiskScore(
                    company_sk=company_sk,
                    scenario_sk=scenario_sk,
                    horizon_year=horizon_year,
                    run_sk=run_sk,
                    score_0_100=result.band.central,
                    band_low=result.band.low,
                    band_high=result.band.high,
                    n_assets=asset_counts.get(company_sk, 0),
                    coverage_pct=result.coverage_pct,
                )
            )
            scored += 1
            logger.info(
                "score_physical: empresa=%s cenário=%s horizonte=%s score=%.1f [%.1f, %.1f] cobertura=%.0f%%",
                company_sk,
                scenario_name,
                horizon_year,
                result.band.central,
                result.band.low,
                result.band.high,
                result.coverage_pct,
            )

    logger.info("score_physical: %d empresas pontuadas (run_sk=%s)", scored, run_sk)
    return scored


@flow(name="compute-scores")
def compute_scores_flow(
    scenario_name: str = "historical",
    horizons: tuple[int, ...] = (2030, 2040, 2050),
) -> dict[str, Any]:
    """Calcula o score físico para um cenário em cada horizonte."""
    return {str(h): score_physical(scenario_name, h) for h in horizons}
