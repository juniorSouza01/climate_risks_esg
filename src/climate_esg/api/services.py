from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
from sqlalchemy.orm import Session

from climate_esg.api.schemas.scores import (
    BandOut,
    ExplanationOut,
    FinancialOut,
    HazardOut,
    ModelCardOut,
    PortfolioCompany,
    PortfolioOut,
    RunInfo,
    RunOut,
    ScoreEntry,
    TransitionDetail,
)
from climate_esg.db.models import (
    DimCompany,
    DimModelRun,
    DimScenario,
    FactFinancialImpact,
    FactHazardExposure,
    FactPhysicalRiskScore,
    FactScoreExplanation,
    FactTransitionRiskScore,
)
from climate_esg.governance.audit import list_runs, run_fact_counts
from climate_esg.governance.model_cards import build_model_card
from climate_esg.modeling.scoring import ScoreBand, compose_score

ScoreTable = type[FactPhysicalRiskScore] | type[FactTransitionRiskScore]


def _f(value: float | None) -> float | None:
    return float(value) if value is not None else None


def _band_out(band: ScoreBand) -> BandOut:
    return BandOut(central=band.central, low=band.low, high=band.high)


def _run_info(run_sk: int, model_version: str, computed_at: dt.datetime | None) -> RunInfo:
    return RunInfo(
        run_sk=int(run_sk),
        model_version=str(model_version),
        computed_at=computed_at.isoformat() if computed_at is not None else "",
    )


def _physical_rows(
    session: Session, company_sk: int
) -> dict[tuple[int, int], tuple[ScoreBand, RunInfo]]:
    f = FactPhysicalRiskScore
    latest = (
        sa.select(f.scenario_sk, f.horizon_year, sa.func.max(f.run_sk).label("run_sk"))
        .where(f.company_sk == company_sk)
        .group_by(f.scenario_sk, f.horizon_year)
        .subquery()
    )
    rows = session.execute(
        sa.select(
            f.scenario_sk,
            f.horizon_year,
            f.score_0_100,
            f.band_low,
            f.band_high,
            f.run_sk,
            DimModelRun.model_version,
            f.computed_at,
        )
        .where(f.company_sk == company_sk)
        .join(
            latest,
            sa.and_(
                f.scenario_sk == latest.c.scenario_sk,
                f.horizon_year == latest.c.horizon_year,
                f.run_sk == latest.c.run_sk,
            ),
        )
        .join(DimModelRun, DimModelRun.run_sk == f.run_sk)
    ).all()
    out: dict[tuple[int, int], tuple[ScoreBand, RunInfo]] = {}
    for scen, hor, central, low, high, run_sk, mver, computed in rows:
        band = ScoreBand(central=float(central), low=float(low), high=float(high))
        out[(scen, hor)] = (band, _run_info(run_sk, mver, computed))
    return out


def _transition_rows(
    session: Session, company_sk: int
) -> dict[tuple[int, int], tuple[ScoreBand, TransitionDetail, RunInfo]]:
    f = FactTransitionRiskScore
    latest = (
        sa.select(f.scenario_sk, f.horizon_year, sa.func.max(f.run_sk).label("run_sk"))
        .where(f.company_sk == company_sk)
        .group_by(f.scenario_sk, f.horizon_year)
        .subquery()
    )
    rows = session.execute(
        sa.select(
            f.scenario_sk,
            f.horizon_year,
            f.score_0_100,
            f.band_low,
            f.band_high,
            f.run_sk,
            DimModelRun.model_version,
            f.computed_at,
            f.sub_score_policy,
            f.sub_score_tech,
            f.sub_score_market,
            f.carbon_intensity,
            f.target_alignment,
        )
        .where(f.company_sk == company_sk)
        .join(
            latest,
            sa.and_(
                f.scenario_sk == latest.c.scenario_sk,
                f.horizon_year == latest.c.horizon_year,
                f.run_sk == latest.c.run_sk,
            ),
        )
        .join(DimModelRun, DimModelRun.run_sk == f.run_sk)
    ).all()
    out: dict[tuple[int, int], tuple[ScoreBand, TransitionDetail, RunInfo]] = {}
    for row in rows:
        band = ScoreBand(central=float(row[2]), low=float(row[3]), high=float(row[4]))
        detail = TransitionDetail(
            policy=_f(row[8]),
            tech=_f(row[9]),
            market=_f(row[10]),
            carbon_intensity=_f(row[11]),
            target_alignment=_f(row[12]),
        )
        out[(row[0], row[1])] = (band, detail, _run_info(row[5], row[6], row[7]))
    return out


def company_scores(session: Session, company_sk: int) -> list[ScoreEntry]:
    physical = _physical_rows(session, company_sk)
    transition = _transition_rows(session, company_sk)
    scenario_names: dict[int, str] = {
        sk: name
        for sk, name in session.execute(sa.select(DimScenario.scenario_sk, DimScenario.name)).all()
    }

    entries: list[ScoreEntry] = []
    for scenario_sk, horizon_year in sorted(set(physical) | set(transition)):
        phys = physical.get((scenario_sk, horizon_year))
        trans = transition.get((scenario_sk, horizon_year))
        composite = compose_score(phys[0], trans[0]) if phys and trans else None
        entries.append(
            ScoreEntry(
                scenario=scenario_names.get(scenario_sk, str(scenario_sk)),
                horizon_year=horizon_year,
                physical=_band_out(phys[0]) if phys else None,
                transition=_band_out(trans[0]) if trans else None,
                composite=_band_out(composite) if composite else None,
                transition_detail=trans[1] if trans else None,
                physical_run=phys[1] if phys else None,
                transition_run=trans[2] if trans else None,
            )
        )
    return entries


def company_explanations(session: Session, company_sk: int) -> list[ExplanationOut]:
    f = FactScoreExplanation
    latest = (
        sa.select(f.scenario_sk, f.horizon_year, sa.func.max(f.run_sk).label("run_sk"))
        .where(f.company_sk == company_sk)
        .group_by(f.scenario_sk, f.horizon_year)
        .subquery()
    )
    rows = session.execute(
        sa.select(
            f.scenario_sk,
            f.horizon_year,
            f.narrative_md,
            f.drivers,
            f.run_sk,
            f.computed_at,
            DimScenario.name,
        )
        .where(f.company_sk == company_sk)
        .join(
            latest,
            sa.and_(
                f.scenario_sk == latest.c.scenario_sk,
                f.horizon_year == latest.c.horizon_year,
                f.run_sk == latest.c.run_sk,
            ),
        )
        .join(DimScenario, DimScenario.scenario_sk == f.scenario_sk)
        .order_by(f.scenario_sk, f.horizon_year)
    ).all()
    return [
        ExplanationOut(
            scenario=str(name),
            horizon_year=int(hor),
            narrative_md=str(narrative),
            drivers=drivers,
            run_sk=int(run_sk),
            computed_at=computed.isoformat() if computed is not None else "",
        )
        for _scen, hor, narrative, drivers, run_sk, computed, name in rows
    ]


def company_financial(session: Session, company_sk: int) -> list[FinancialOut]:
    f = FactFinancialImpact
    latest = (
        sa.select(f.scenario_sk, f.horizon_year, sa.func.max(f.run_sk).label("run_sk"))
        .where(f.company_sk == company_sk)
        .group_by(f.scenario_sk, f.horizon_year)
        .subquery()
    )
    rows = session.execute(
        sa.select(
            f.horizon_year,
            f.dcf_adjustment_pct,
            f.band_low_pct,
            f.band_high_pct,
            f.run_sk,
            DimScenario.name,
        )
        .where(f.company_sk == company_sk)
        .join(
            latest,
            sa.and_(
                f.scenario_sk == latest.c.scenario_sk,
                f.horizon_year == latest.c.horizon_year,
                f.run_sk == latest.c.run_sk,
            ),
        )
        .join(DimScenario, DimScenario.scenario_sk == f.scenario_sk)
        .order_by(DimScenario.name, f.horizon_year)
    ).all()
    return [
        FinancialOut(
            scenario=str(name),
            horizon_year=int(hor),
            dcf_adjustment_pct=float(adj),
            band_low_pct=float(low),
            band_high_pct=float(high),
            run_sk=int(run_sk),
        )
        for hor, adj, low, high, run_sk, name in rows
    ]


def list_model_runs(session: Session) -> list[RunOut]:
    return [
        RunOut(
            run_sk=r.run_sk,
            model_name=r.model_name,
            model_version=r.model_version,
            code_commit=r.code_commit,
            created_at=r.created_at.isoformat() if r.created_at is not None else "",
        )
        for r in list_runs(session)
    ]


def model_card(session: Session, run_sk: int) -> ModelCardOut | None:
    run = session.get(DimModelRun, run_sk)
    if run is None:
        return None
    markdown = build_model_card(
        run_sk=run.run_sk,
        model_name=run.model_name,
        model_version=run.model_version,
        code_commit=run.code_commit,
        train_data_version=run.train_data_version,
        hyperparams=run.hyperparams,
        created_at=run.created_at,
    )
    return ModelCardOut(
        run_sk=run.run_sk,
        markdown=markdown,
        fact_counts=run_fact_counts(session, run_sk),
    )


def asset_hazards(session: Session, asset_sk: int) -> list[HazardOut]:
    f = FactHazardExposure
    latest = (
        sa.select(
            f.hazard_type,
            f.scenario_sk,
            f.horizon_year,
            sa.func.max(f.run_sk).label("run_sk"),
        )
        .where(f.asset_sk == asset_sk)
        .group_by(f.hazard_type, f.scenario_sk, f.horizon_year)
        .subquery()
    )
    rows = session.execute(
        sa.select(
            f.hazard_type,
            f.horizon_year,
            f.exposure_normalized,
            f.run_sk,
            DimScenario.name,
        )
        .where(f.asset_sk == asset_sk)
        .join(
            latest,
            sa.and_(
                f.hazard_type == latest.c.hazard_type,
                f.scenario_sk == latest.c.scenario_sk,
                f.horizon_year == latest.c.horizon_year,
                f.run_sk == latest.c.run_sk,
            ),
        )
        .join(DimScenario, DimScenario.scenario_sk == f.scenario_sk)
        .order_by(DimScenario.name, f.horizon_year, f.hazard_type)
    ).all()
    return [
        HazardOut(
            hazard_type=str(hazard),
            scenario=str(name),
            horizon_year=int(hor),
            exposure_normalized=float(exposure),
            run_sk=int(run_sk),
        )
        for hazard, hor, exposure, run_sk, name in rows
    ]


def _bands_all_companies(
    session: Session, table: ScoreTable, scenario_sk: int, horizon_year: int
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


def portfolio(session: Session, scenario_name: str, horizon_year: int) -> PortfolioOut | None:
    scenario_sk = session.scalar(
        sa.select(DimScenario.scenario_sk).where(DimScenario.name == scenario_name)
    )
    if scenario_sk is None:
        return None

    physical = _bands_all_companies(session, FactPhysicalRiskScore, scenario_sk, horizon_year)
    transition = _bands_all_companies(session, FactTransitionRiskScore, scenario_sk, horizon_year)
    names: dict[int, str] = {
        sk: name
        for sk, name in session.execute(sa.select(DimCompany.company_sk, DimCompany.name)).all()
    }

    companies: list[PortfolioCompany] = []
    composites: list[float] = []
    for company_sk in sorted(set(physical) | set(transition)):
        phys = physical.get(company_sk)
        trans = transition.get(company_sk)
        composite = compose_score(phys, trans) if phys and trans else None
        if composite is not None:
            composites.append(composite.central)
        companies.append(
            PortfolioCompany(
                company_sk=company_sk,
                name=names.get(company_sk, str(company_sk)),
                composite=_band_out(composite) if composite else None,
            )
        )

    avg = round(sum(composites) / len(composites), 2) if composites else None
    return PortfolioOut(
        scenario=scenario_name,
        horizon_year=horizon_year,
        n_companies=len(companies),
        avg_composite=avg,
        companies=companies,
    )
