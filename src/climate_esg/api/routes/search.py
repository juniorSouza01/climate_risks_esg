from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from climate_esg.api.deps import get_session
from climate_esg.api.schemas.scores import DossierOut
from climate_esg.config import get_settings
from climate_esg.search.dossier import get_or_build_dossier

router = APIRouter(tags=["search"])


@router.get("/search", response_model=DossierOut)
def search(
    q: str = Query(..., min_length=2, description="CNPJ, ticker ou nome"),
    session: Session = Depends(get_session),
) -> DossierOut:
    payload = get_or_build_dossier(session, q, ttl_s=get_settings().dossier_cache_ttl_s)
    return DossierOut(**payload)
