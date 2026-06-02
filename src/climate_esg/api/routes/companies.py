from __future__ import annotations

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from climate_esg.api.deps import get_session
from climate_esg.api.schemas.scores import CompanyOut, CompanyScores
from climate_esg.api.services import company_scores
from climate_esg.db.models import DimCompany

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
