from __future__ import annotations

from pydantic import BaseModel


class BandOut(BaseModel):
    central: float
    low: float
    high: float


class ScoreEntry(BaseModel):
    scenario: str
    horizon_year: int
    physical: BandOut | None = None
    transition: BandOut | None = None
    composite: BandOut | None = None


class CompanyOut(BaseModel):
    company_sk: int
    name: str
    ticker: str | None = None
    sector_nace: str | None = None
    is_listed: bool


class CompanyScores(BaseModel):
    company_sk: int
    name: str
    scores: list[ScoreEntry]
