from __future__ import annotations

from collections import defaultdict
from typing import Any

import sqlalchemy as sa
from prefect import flow, get_run_logger, task

from climate_esg.db.base import session_scope
from climate_esg.db.models import (
    DimAsset,
    DimClimateVariable,
    DimCompany,
    DimScenario,
    FactClimateIndicator,
    FactFinancialImpact,
    FactHazardExposure,
    FactPhysicalRiskScore,
    FactScoreExplanation,
    FactTransitionRiskScore,
)
from climate_esg.geospatial.exposure import asset_hazard_exposures
from climate_esg.governance.lineage import start_model_run
from climate_esg.modeling.explanation import build_narrative
from climate_esg.modeling.financial_impact import compute_financial_impact
from climate_esg.modeling.physical_config import (
    HAZARD_WEIGHTS,
    PHYSICAL_MODEL_NAME,
    PHYSICAL_MODEL_VERSION,
)
from climate_esg.modeling.physical_risk import compute_physical_score
from climate_esg.modeling.scoring import ScoreBand, compose_score
from climate_esg.modeling.transition_config import (
    COMPANY_TRANSITION_INPUTS,
    SUBSCORE_WEIGHTS,
    TRANSITION_MODEL_NAME,
    TRANSITION_MODEL_VERSION,
)
from climate_esg.modeling.transition_risk import compute_transition_score
from climate_esg.quality.checks import assert_score_jump, validate_score_rows

EXPLANATION_MODEL_NAME = "score_explanation"
EXPLANATION_MODEL_VERSION = "0.1.0"
HAZARD_EXPOSURE_MODEL_NAME = "hazard_exposure"
HAZARD_EXPOSURE_MODEL_VERSION = "0.1.0"
FINANCIAL_MODEL_NAME = "financial_dcf"
FINANCIAL_MODEL_VERSION = "0.1.0"


def _flow_logger() -> Any:
    import logging

    try:
        return get_run_logger()
    except Exception:
        return logging.getLogger("climate_esg.compute_scores")


def _scenario_sk(session: sa.orm.Session, scenario_name: str) -> int | None:
    return session.scalar(
        sa.select(DimScenario.scenario_sk).where(DimScenario.name == scenario_name)
    )


def _previous_score(
    session: sa.orm.Session, table: Any, company_sk: int, scenario_sk: int, horizon_year: int
) -> float | None:
    value = session.scalar(
        sa.select(table.score_0_100)
        .where(
            table.company_sk == company_sk,
            table.scenario_sk == scenario_sk,
            table.horizon_year == horizon_year,
        )
        .order_by(table.run_sk.desc())
        .limit(1)
    )
    return float(value) if value is not None else None


@task
def score_physical(scenario_name: str, horizon_year: int) -> int:
    logger = _flow_logger()
    scored = 0

    with session_scope() as session:
        scenario_sk = _scenario_sk(session, scenario_name)
        if scenario_sk is None:
            logger.warning("score_physical: cenário '%s' não existe", scenario_name)
            return 0

        run_sk = start_model_run(
            session,
            model_name=PHYSICAL_MODEL_NAME,
            model_version=PHYSICAL_MODEL_VERSION,
            hyperparams={"weights": HAZARD_WEIGHTS, "horizon_year": horizon_year},
        )

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
                    "score_physical: empresa %s sem variável de hazard mapeável (vars=%s)",
                    company_sk,
                    sorted(means),
                )
                continue

            validate_score_rows(
                [
                    {
                        "score_0_100": result.band.central,
                        "band_low": result.band.low,
                        "band_high": result.band.high,
                    }
                ]
            )
            assert_score_jump(
                _previous_score(
                    session, FactPhysicalRiskScore, company_sk, scenario_sk, horizon_year
                ),
                result.band.central,
            )

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
        "score_physical: %d empresas (cenário=%s h=%s)", scored, scenario_name, horizon_year
    )
    return scored


@task
def score_transition(scenario_name: str, horizon_year: int) -> int:
    logger = _flow_logger()
    scored = 0

    with session_scope() as session:
        scenario_sk = _scenario_sk(session, scenario_name)
        if scenario_sk is None:
            logger.warning("score_transition: cenário '%s' não existe", scenario_name)
            return 0

        run_sk = start_model_run(
            session,
            model_name=TRANSITION_MODEL_NAME,
            model_version=TRANSITION_MODEL_VERSION,
            hyperparams={"weights": SUBSCORE_WEIGHTS, "horizon_year": horizon_year},
        )

        for company_sk, inp in COMPANY_TRANSITION_INPUTS.items():
            result = compute_transition_score(inp.policy, inp.tech, inp.market)
            validate_score_rows(
                [
                    {
                        "score_0_100": result.band.central,
                        "band_low": result.band.low,
                        "band_high": result.band.high,
                    }
                ]
            )
            assert_score_jump(
                _previous_score(
                    session, FactTransitionRiskScore, company_sk, scenario_sk, horizon_year
                ),
                result.band.central,
            )
            session.add(
                FactTransitionRiskScore(
                    company_sk=company_sk,
                    scenario_sk=scenario_sk,
                    horizon_year=horizon_year,
                    run_sk=run_sk,
                    score_0_100=result.band.central,
                    band_low=result.band.low,
                    band_high=result.band.high,
                    carbon_intensity=inp.carbon_intensity,
                    target_alignment=inp.target_alignment,
                    sub_score_policy=result.sub_score_policy,
                    sub_score_tech=result.sub_score_tech,
                    sub_score_market=result.sub_score_market,
                )
            )
            scored += 1

    logger.info(
        "score_transition: %d empresas (cenário=%s h=%s)", scored, scenario_name, horizon_year
    )
    return scored


def _latest_bands(
    session: sa.orm.Session, table: Any, scenario_sk: int, horizon_year: int
) -> dict[int, ScoreBand]:
    latest = (
        sa.select(table.company_sk, sa.func.max(table.run_sk).label("run_sk"))
        .where(table.scenario_sk == scenario_sk, table.horizon_year == horizon_year)
        .group_by(table.company_sk)
        .subquery()
    )
    rows = session.execute(
        sa.select(table.company_sk, table.score_0_100, table.band_low, table.band_high).join(
            latest,
            sa.and_(
                table.company_sk == latest.c.company_sk,
                table.run_sk == latest.c.run_sk,
            ),
        )
    ).all()
    return {
        company_sk: ScoreBand(central=float(c), low=float(lo), high=float(hi))
        for company_sk, c, lo, hi in rows
    }


@task
def score_composite(scenario_name: str, horizon_year: int) -> list[dict[str, Any]]:
    logger = _flow_logger()
    composed: list[dict[str, Any]] = []

    with session_scope() as session:
        scenario_sk = _scenario_sk(session, scenario_name)
        if scenario_sk is None:
            return []

        physical = _latest_bands(session, FactPhysicalRiskScore, scenario_sk, horizon_year)
        transition = _latest_bands(session, FactTransitionRiskScore, scenario_sk, horizon_year)

        for company_sk in sorted(set(physical) & set(transition)):
            band = compose_score(physical[company_sk], transition[company_sk])
            composed.append(
                {
                    "company_sk": company_sk,
                    "horizon_year": horizon_year,
                    "central": round(band.central, 2),
                    "low": round(band.low, 2),
                    "high": round(band.high, 2),
                }
            )
            logger.info(
                "composite: empresa=%s h=%s score=%.1f [%.1f, %.1f]",
                company_sk,
                horizon_year,
                band.central,
                band.low,
                band.high,
            )

    return composed


def _opt_float(value: float | None) -> float | None:
    return float(value) if value is not None else None


def _latest_physical_coverage(
    session: sa.orm.Session, scenario_sk: int, horizon_year: int
) -> dict[int, float]:
    f = FactPhysicalRiskScore
    latest = (
        sa.select(f.company_sk, sa.func.max(f.run_sk).label("run_sk"))
        .where(f.scenario_sk == scenario_sk, f.horizon_year == horizon_year)
        .group_by(f.company_sk)
        .subquery()
    )
    rows = session.execute(
        sa.select(f.company_sk, f.coverage_pct).join(
            latest,
            sa.and_(f.company_sk == latest.c.company_sk, f.run_sk == latest.c.run_sk),
        )
    ).all()
    return {company_sk: float(cov) for company_sk, cov in rows}


def _latest_transition_subs(
    session: sa.orm.Session, scenario_sk: int, horizon_year: int
) -> dict[int, dict[str, float | None]]:
    f = FactTransitionRiskScore
    latest = (
        sa.select(f.company_sk, sa.func.max(f.run_sk).label("run_sk"))
        .where(f.scenario_sk == scenario_sk, f.horizon_year == horizon_year)
        .group_by(f.company_sk)
        .subquery()
    )
    rows = session.execute(
        sa.select(f.company_sk, f.sub_score_policy, f.sub_score_tech, f.sub_score_market).join(
            latest,
            sa.and_(f.company_sk == latest.c.company_sk, f.run_sk == latest.c.run_sk),
        )
    ).all()
    return {
        company_sk: {
            "policy": _opt_float(policy),
            "tech": _opt_float(tech),
            "market": _opt_float(market),
        }
        for company_sk, policy, tech, market in rows
    }


@task
def score_explanation(scenario_name: str, horizon_year: int) -> int:
    logger = _flow_logger()
    written = 0

    with session_scope() as session:
        scenario_sk = _scenario_sk(session, scenario_name)
        if scenario_sk is None:
            return 0

        run_sk = start_model_run(
            session,
            model_name=EXPLANATION_MODEL_NAME,
            model_version=EXPLANATION_MODEL_VERSION,
            hyperparams={"horizon_year": horizon_year, "method": "deterministic_template"},
        )

        physical = _latest_bands(session, FactPhysicalRiskScore, scenario_sk, horizon_year)
        transition = _latest_bands(session, FactTransitionRiskScore, scenario_sk, horizon_year)
        coverage = _latest_physical_coverage(session, scenario_sk, horizon_year)
        subs = _latest_transition_subs(session, scenario_sk, horizon_year)
        names = dict(session.execute(sa.select(DimCompany.company_sk, DimCompany.name)).all())

        for company_sk in sorted(set(physical) | set(transition)):
            phys = physical.get(company_sk)
            trans = transition.get(company_sk)
            composite = compose_score(phys, trans) if phys and trans else None
            narrative = build_narrative(
                company_name=names.get(company_sk, str(company_sk)),
                scenario=scenario_name,
                horizon_year=horizon_year,
                physical=phys,
                transition=trans,
                composite=composite,
                sub_scores=subs.get(company_sk, {}),
                coverage_pct=coverage.get(company_sk, 0.0),
            )
            session.add(
                FactScoreExplanation(
                    company_sk=company_sk,
                    scenario_sk=scenario_sk,
                    horizon_year=horizon_year,
                    run_sk=run_sk,
                    narrative_md=narrative.text,
                    drivers=narrative.drivers,
                    sources=[],
                )
            )
            written += 1

    logger.info(
        "score_explanation: %d narrativas (cenário=%s h=%s)", written, scenario_name, horizon_year
    )
    return written


@task
def score_hazard_exposure(scenario_name: str, horizon_year: int) -> int:
    logger = _flow_logger()
    written = 0

    with session_scope() as session:
        scenario_sk = _scenario_sk(session, scenario_name)
        if scenario_sk is None:
            return 0

        run_sk = start_model_run(
            session,
            model_name=HAZARD_EXPOSURE_MODEL_NAME,
            model_version=HAZARD_EXPOSURE_MODEL_VERSION,
            hyperparams={"horizon_year": horizon_year},
        )

        rows = session.execute(
            sa.select(
                FactClimateIndicator.asset_sk,
                DimClimateVariable.cf_code,
                sa.func.avg(FactClimateIndicator.value_mean),
            )
            .join(
                DimClimateVariable,
                DimClimateVariable.var_sk == FactClimateIndicator.var_sk,
            )
            .where(FactClimateIndicator.scenario_sk == scenario_sk)
            .group_by(FactClimateIndicator.asset_sk, DimClimateVariable.cf_code)
        ).all()

        by_asset: dict[int, dict[str, float]] = defaultdict(dict)
        for asset_sk, cf_code, avg_value in rows:
            if avg_value is not None:
                by_asset[asset_sk][cf_code] = float(avg_value)

        for asset_sk, var_means in by_asset.items():
            for hazard, exposure in asset_hazard_exposures(var_means).items():
                session.add(
                    FactHazardExposure(
                        asset_sk=asset_sk,
                        hazard_type=hazard,
                        scenario_sk=scenario_sk,
                        horizon_year=horizon_year,
                        run_sk=run_sk,
                        exposure_normalized=round(exposure, 4),
                    )
                )
                written += 1

    logger.info(
        "score_hazard_exposure: %d exposições (cenário=%s h=%s)",
        written,
        scenario_name,
        horizon_year,
    )
    return written


@task
def score_financial(scenario_name: str, horizon_year: int) -> int:
    logger = _flow_logger()
    written = 0

    with session_scope() as session:
        scenario_sk = _scenario_sk(session, scenario_name)
        if scenario_sk is None:
            return 0

        run_sk = start_model_run(
            session,
            model_name=FINANCIAL_MODEL_NAME,
            model_version=FINANCIAL_MODEL_VERSION,
            hyperparams={"horizon_year": horizon_year},
        )

        physical = _latest_bands(session, FactPhysicalRiskScore, scenario_sk, horizon_year)
        transition = _latest_bands(session, FactTransitionRiskScore, scenario_sk, horizon_year)

        for company_sk in sorted(set(physical) & set(transition)):
            composite = compose_score(physical[company_sk], transition[company_sk])
            impact = compute_financial_impact(composite, scenario=scenario_name)
            session.add(
                FactFinancialImpact(
                    company_sk=company_sk,
                    scenario_sk=scenario_sk,
                    horizon_year=horizon_year,
                    run_sk=run_sk,
                    dcf_adjustment_pct=impact.dcf_adjustment_pct,
                    band_low_pct=impact.band_low_pct,
                    band_high_pct=impact.band_high_pct,
                )
            )
            written += 1

    logger.info(
        "score_financial: %d empresas (cenário=%s h=%s)", written, scenario_name, horizon_year
    )
    return written


def compute_all(
    scenario_name: str = "historical",
    horizons: tuple[int, ...] = (2030, 2040, 2050),
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for h in horizons:
        result[str(h)] = {
            "hazard_exposure": score_hazard_exposure.fn(scenario_name, h),
            "physical": score_physical.fn(scenario_name, h),
            "transition": score_transition.fn(scenario_name, h),
            "composite": score_composite.fn(scenario_name, h),
            "explanation": score_explanation.fn(scenario_name, h),
            "financial": score_financial.fn(scenario_name, h),
        }
    return result


@flow(name="compute-scores")
def compute_scores_flow(
    scenario_name: str = "historical",
    horizons: tuple[int, ...] = (2030, 2040, 2050),
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for h in horizons:
        exposure = score_hazard_exposure(scenario_name, h)
        physical = score_physical(scenario_name, h)
        transition = score_transition(scenario_name, h)
        composite = score_composite(scenario_name, h)
        explanation = score_explanation(scenario_name, h)
        financial = score_financial(scenario_name, h)
        result[str(h)] = {
            "hazard_exposure": exposure,
            "physical": physical,
            "transition": transition,
            "composite": composite,
            "explanation": explanation,
            "financial": financial,
        }
    return result


if __name__ == "__main__":
    import sys

    _scenario = sys.argv[1] if len(sys.argv) > 1 else "historical"
    _horizons = tuple(int(x) for x in sys.argv[2:]) or (2030, 2040, 2050)
    _out = compute_all(_scenario, _horizons)
    print(f"\ncompute_all('{_scenario}', {_horizons}):")
    for hz, counts in _out.items():
        print(
            f"  h={hz}: exposições={counts['hazard_exposure']} físico={counts['physical']} "
            f"transição={counts['transition']} explicações={counts['explanation']} "
            f"financeiro={counts['financial']}"
        )
