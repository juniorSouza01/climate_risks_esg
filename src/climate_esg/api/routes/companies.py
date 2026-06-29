from __future__ import annotations

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from climate_esg.api.deps import get_session
from climate_esg.api.schemas.scores import (
    AssetOut,
    CompanyOut,
    CompanyScores,
    ExplanationOut,
    FinancialOut,
    HazardOut,
    ModelCardOut,
    PortfolioOut,
    RunOut,
)
from climate_esg.api.services import (
    asset_hazards,
    company_explanations,
    company_financial,
    company_scores,
    list_model_runs,
    model_card,
    portfolio,
)
from climate_esg.db.models import DimAsset, DimCompany

router = APIRouter(tags=["companies"])


@router.get("/companies", response_model=list[CompanyOut])
def list_companies(session: Session = Depends(get_session)) -> list[CompanyOut]:
    companies = session.scalars(sa.select(DimCompany).order_by(DimCompany.company_sk)).all()
    return [
        CompanyOut(
            company_sk=c.company_sk,
            name=c.name,
            ticker=c.ticker,
            sector_nace=c.sector_nace,
            is_listed=c.is_listed,
        )
        for c in companies
    ]


@router.get("/companies/{company_sk}/scores", response_model=CompanyScores)
def get_company_scores(company_sk: int, session: Session = Depends(get_session)) -> CompanyScores:
    company = session.get(DimCompany, company_sk)
    if company is None:
        raise HTTPException(status_code=404, detail="empresa não encontrada")
    return CompanyScores(
        company_sk=company_sk,
        name=company.name,
        scores=company_scores(session, company_sk),
    )


@router.get("/companies/{company_sk}/explanations", response_model=list[ExplanationOut])
def get_explanations(
    company_sk: int, session: Session = Depends(get_session)
) -> list[ExplanationOut]:
    if session.get(DimCompany, company_sk) is None:
        raise HTTPException(status_code=404, detail="empresa não encontrada")
    return company_explanations(session, company_sk)


@router.get("/companies/{company_sk}/financial", response_model=list[FinancialOut])
def get_financial(company_sk: int, session: Session = Depends(get_session)) -> list[FinancialOut]:
    if session.get(DimCompany, company_sk) is None:
        raise HTTPException(status_code=404, detail="empresa não encontrada")
    return company_financial(session, company_sk)


@router.get("/assets/{asset_sk}/hazards", response_model=list[HazardOut])
def get_asset_hazards(asset_sk: int, session: Session = Depends(get_session)) -> list[HazardOut]:
    return asset_hazards(session, asset_sk)


@router.get("/runs", response_model=list[RunOut])
def get_runs(session: Session = Depends(get_session)) -> list[RunOut]:
    return list_model_runs(session)


@router.get("/model-cards/{run_sk}", response_model=ModelCardOut)
def get_model_card(run_sk: int, session: Session = Depends(get_session)) -> ModelCardOut:
    card = model_card(session, run_sk)
    if card is None:
        raise HTTPException(status_code=404, detail="run não encontrado")
    return card


@router.get("/portfolio", response_model=PortfolioOut)
def get_portfolio(
    scenario: str = "historical",
    horizon: int = 2030,
    session: Session = Depends(get_session),
) -> PortfolioOut:
    result = portfolio(session, scenario, horizon)
    if result is None:
        raise HTTPException(status_code=404, detail="cenário não encontrado")
    return result


@router.get("/companies/{company_sk}/assets", response_model=list[AssetOut])
def list_assets(company_sk: int, session: Session = Depends(get_session)) -> list[AssetOut]:
    assets = session.scalars(
        sa.select(DimAsset).where(DimAsset.company_sk == company_sk).order_by(DimAsset.asset_sk)
    ).all()
    return [
        AssetOut(
            asset_sk=a.asset_sk,
            name=a.name,
            asset_type=a.asset_type,
            latitude=float(a.latitude) if a.latitude is not None else None,
            longitude=float(a.longitude) if a.longitude is not None else None,
            municipality=a.municipality,
            state=a.state,
        )
        for a in assets
    ]
