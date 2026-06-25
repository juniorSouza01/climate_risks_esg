"""FastAPI entrypoint. No F0 expõe apenas /health e /version."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from climate_esg import __version__
from climate_esg.api.routes.companies import router as companies_router

app = FastAPI(
    title="Climate ESG Platform API",
    version=__version__,
    description="API privada da Plataforma de Análise de Riscos Climáticos para ESG.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:4173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(companies_router, prefix="/v1")


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/version", tags=["meta"])
def version() -> dict[str, str]:
    return {"version": __version__}
