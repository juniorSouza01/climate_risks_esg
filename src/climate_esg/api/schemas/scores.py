from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

Availability = Literal["available", "not_computed", "no_data"]


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
    availability: Availability = "available"
    reason: str | None = None


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


class PeerOut(BaseModel):
    company_sk: int
    name: str
    distance: float


class AnomalyOut(BaseModel):
    company_sk: int
    name: str
    score: float
    is_outlier: bool


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


SectionStatus = Literal["ok", "no_input", "insufficient_universe", "unresolved", "error"]
DossierStatus = Literal["complete", "degraded"]


class SectionErrorOut(BaseModel):
    source: str
    code: str
    transient: bool = False


class ArticleOut(BaseModel):
    title: str
    url: str
    domain: str
    seendate: str


class NewsOut(BaseModel):
    status: SectionStatus = "ok"
    reason: str | None = None
    articles: list[ArticleOut] = []


class MarketOut(BaseModel):
    status: SectionStatus = "ok"
    reason: str | None = None
    ticker: str | None = None
    name: str | None = None
    currency: str | None = None
    price: float | None = None
    market_cap: float | None = None
    pe_ratio: float | None = None
    annualized_volatility: float | None = None
    n_observations: int | None = None
    confidence: Literal["exact", "heuristic"] | None = None


class SecondaryCnaeOut(BaseModel):
    codigo: int | str | None = None
    descricao: str | None = None


class RegistryOut(BaseModel):
    cnpj: str | None = None
    razao_social: str | None = None
    nome_fantasia: str | None = None
    cnae: str | None = None
    cnae_codigo: int | str | None = None
    cnaes_secundarios: list[SecondaryCnaeOut] = []
    situacao: str | None = None
    porte: str | None = None
    natureza_juridica: str | None = None
    capital_social: float | str | None = None
    data_inicio_atividade: str | None = None
    logradouro: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cep: str | None = None
    uf: str | None = None
    municipio: str | None = None
    telefone: str | None = None
    socios: list[str] = []


class ClimateHazardOut(BaseModel):
    value: float | None = None
    label: str | None = None


class ClimateMetaOut(BaseModel):
    source: str | None = None
    scenario: str | None = None
    horizon: int | None = None
    municipio: str | None = None
    uf: str | None = None
    ibge: str | None = None
    scale: str | None = None


class FinancialHistoryOut(BaseModel):
    fiscal_year: int
    revenue: float | None = None
    ebitda: float | None = None
    net_income: float | None = None


class FinancialsOut(BaseModel):
    cnpj: str | None = None
    revenue: float | None = None
    net_income: float | None = None
    ebit: float | None = None
    ebitda: float | None = None
    total_assets: float | None = None
    equity: float | None = None
    gross_debt: float | None = None
    net_margin: float | None = None
    ebitda_margin: float | None = None
    debt_to_ebitda: float | None = None
    roe: float | None = None
    revenue_growth: float | None = None
    history: list[FinancialHistoryOut] | None = None
    fiscal_year: int
    source: str | None = None


class ClimateIndexOut(BaseModel):
    value: float
    label: str
    basis: str


class RevenueAtRiskOut(BaseModel):
    pct_low: float
    pct_central: float
    pct_high: float
    brl_low: float
    brl_central: float
    brl_high: float
    basis: str
    seal: str


class PercentileOut(BaseModel):
    value: float
    n: int
    basis: str


class CrossOut(BaseModel):
    status: SectionStatus = "ok"
    reason: str | None = None
    climate_index: ClimateIndexOut | None = None
    revenue_at_risk: RevenueAtRiskOut | None = None
    revenue_percentile: PercentileOut | None = None
    ebitda_margin_percentile: PercentileOut | None = None
    narrative: str | None = None


class SegmentOut(BaseModel):
    cluster: int
    label: str
    n_in_cluster: int
    n_total: int
    basis: str
    seal: str


class PeerItemOut(BaseModel):
    cnpj: str | None = None
    denom: str | None = None
    distance: float


class PeersOut(BaseModel):
    items: list[PeerItemOut] = []
    basis: str | None = None
    seal: str | None = None


class AnomalySectionOut(BaseModel):
    is_outlier: bool
    score: float
    basis: str | None = None
    seal: str | None = None


class PredictionsOut(BaseModel):
    status: SectionStatus = "ok"
    reason: str | None = None
    segment: SegmentOut | None = None
    peers: PeersOut | None = None
    anomaly: AnomalySectionOut | None = None


class SectorOut(BaseModel):
    cnae: str | None = None
    division: str | None = None
    archetype: str
    assumed: bool = False
    sensitivities: dict[str, float] = {}


class ImpactBandOut(BaseModel):
    low: float
    central: float
    high: float


class ChannelOut(BaseModel):
    label: str
    statement: str
    brl: ImpactBandOut | None = None
    pp: ImpactBandOut | None = None
    pct_base: float | None = None


class RiskAdjustedOut(BaseModel):
    value: float
    label: str
    basis: str


class ClimateFinancialOut(BaseModel):
    status: SectionStatus = "ok"
    reason: str | None = None
    sector: SectorOut | None = None
    physical_exposure: float | None = None
    climate_index: float | None = None
    channels: dict[str, ChannelOut] | None = None
    materialidade: float | None = None
    risco_ajustado: RiskAdjustedOut | None = None
    narrative: str | None = None
    seal: str | None = None


class SupplierOut(BaseModel):
    division: str | None = None
    label: str | None = None
    archetype: str | None = None
    dominant_hazard: str | None = None
    exposure_index: float | None = None
    fragility: float | None = None
    disruption_index: float | None = None


class SupplyChainOut(BaseModel):
    status: SectionStatus = "ok"
    reason: str | None = None
    suppliers: list[SupplierOut] | None = None
    chain_risk_index: float | None = None
    dependence_raw_material: float | None = None
    production_at_risk_brl: ImpactBandOut | None = None
    production_at_risk_pct_ebitda: float | None = None
    national_hazard_means: dict[str, float] | None = None
    methodology: str | None = None
    narrative: str | None = None
    seal: str | None = None


class RelationshipsOut(BaseModel):
    cnpj: str | None = None
    gov_supplier: dict[str, Any] | None = None
    socios: dict[str, Any] | None = None
    value_chain: dict[str, Any] | None = None
    public_contracts: dict[str, Any] | None = None


class DossierOut(BaseModel):
    query: str
    kind: str
    status: DossierStatus = "complete"
    name: str | None = None
    registry: RegistryOut | None = None
    market: MarketOut | None = None
    news: NewsOut = NewsOut()
    controversy_ratio: float | None = None
    sources: list[str] = []
    errors: list[SectionErrorOut] = []
    fetched_at: str | None = None
    cached: bool = False
    company_sk: int | None = None
    ibge_code: str | None = None
    climate_risk: dict[str, ClimateHazardOut] = {}
    climate_meta: ClimateMetaOut = ClimateMetaOut()
    financials: FinancialsOut | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_label: str | None = None
    cross: CrossOut = CrossOut()
    predictions: PredictionsOut = PredictionsOut()
    climate_financial: ClimateFinancialOut = ClimateFinancialOut()
    relationships: RelationshipsOut | None = None
    supply_chain: SupplyChainOut = SupplyChainOut()


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
