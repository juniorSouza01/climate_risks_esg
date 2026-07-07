"""FastAPI entrypoint. No F0 expõe apenas /health e /version."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sqlalchemy as sa
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from climate_esg import __version__
from climate_esg.api.deps import get_session, require_api_key
from climate_esg.api.routes.companies import router as companies_router
from climate_esg.api.routes.search import router as search_router
from climate_esg.config import get_settings
from climate_esg.ingestion.http import close_client
from climate_esg.logging import get_logger

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.pg_password.get_secret_value() == "changeme_local_only":
        log.warning("startup.default_pg_password", pg_user=settings.pg_user, pg_db=settings.pg_db)
    yield
    close_client()


app = FastAPI(
    title="Climate ESG Platform API",
    version=__version__,
    description="API privada da Plataforma de Análise de Riscos Climáticos para ESG.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(companies_router, prefix="/v1")
app.include_router(search_router, prefix="/v1", dependencies=[Depends(require_api_key)])


@app.get("/health", tags=["meta"])
def health(session: Session = Depends(get_session)) -> dict[str, str]:
    try:
        session.execute(sa.text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database indisponível") from exc
    return {"status": "ok"}


@app.get("/version", tags=["meta"])
def version() -> dict[str, str]:
    return {"version": __version__}
