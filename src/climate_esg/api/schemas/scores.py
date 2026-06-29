from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class BandOut(BaseModel):
    central: float
    low: float
    high: float


class RunInfo(BaseModel):
    run_sk: int
    model_version: str
    computed_at: str


class TransitionDetail(BaseModel):
    policy: float | None = None
    tech: float | None = None
    market: float | None = None
    carbon_intensity: float | None = None
    target_alignment: float | None = None


class ScoreEntry(BaseModel):
    scenario: str
    horizon_year: int
    physical: BandOut | None = None
    transition: BandOut | None = None
    composite: BandOut | None = None
    transition_detail: TransitionDetail | None = None
    physical_run: RunInfo | None = None
    transition_run: RunInfo | None = None


class CompanyOut(BaseModel):
    company_sk: int
    name: str
    ticker: str | None = None
    sector_nace: str | None = None
    is_listed: bool


class AssetOut(BaseModel):
    asset_sk: int
    name: str | None = None
    asset_type: str
    latitude: float | None = None
    longitude: float | None = None
    municipality: str | None = None
    state: str | None = None


class CompanyScores(BaseModel):
    company_sk: int
    name: str
    scores: list[ScoreEntry]


class ExplanationOut(BaseModel):
    scenario: str
    horizon_year: int
    narrative_md: str
    drivers: dict[str, Any] | None = None
    run_sk: int
    computed_at: str


class HazardOut(BaseModel):
    hazard_type: str
    scenario: str
    horizon_year: int
    exposure_normalized: float
    run_sk: int


class PortfolioCompany(BaseModel):
    company_sk: int
    name: str
    composite: BandOut | None = None


class PortfolioOut(BaseModel):
    scenario: str
    horizon_year: int
    n_companies: int
    avg_composite: float | None = None
    companies: list[PortfolioCompany]


class FinancialOut(BaseModel):
    scenario: str
    horizon_year: int
    dcf_adjustment_pct: float
    band_low_pct: float
    band_high_pct: float
    run_sk: int


class RunOut(BaseModel):
    run_sk: int
    model_name: str
    model_version: str
    code_commit: str | None = None
    created_at: str


class ModelCardOut(BaseModel):
    run_sk: int
    markdown: str
    fact_counts: dict[str, int]
