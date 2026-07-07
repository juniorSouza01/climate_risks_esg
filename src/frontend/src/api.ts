export interface Company {
  company_sk: number;
  name: string;
  ticker: string | null;
  sector_nace: string | null;
  is_listed: boolean;
}

export type Availability = "available" | "not_computed" | "no_data";

export type SectionStatus = "ok" | "no_input" | "insufficient_universe" | "unresolved" | "error";

export type DossierStatus = "complete" | "degraded";

export interface DossierSectionError {
  source: string;
  code: string;
  transient?: boolean;
}

export interface NewsArticle {
  title: string;
  url: string;
  domain: string;
  seendate: string;
}

export interface DossierNews {
  status?: SectionStatus;
  reason?: string | null;
  articles: NewsArticle[];
}

export interface DossierMarket {
  status?: SectionStatus;
  reason?: string | null;
  ticker?: string | null;
  name?: string | null;
  currency?: string | null;
  price?: number | null;
  market_cap?: number | null;
  pe_ratio?: number | null;
  annualized_volatility?: number | null;
  n_observations?: number | null;
  confidence?: "exact" | "heuristic" | null;
}

export interface Band {
  central: number;
  low: number;
  high: number;
  availability?: Availability;
  reason?: string | null;
}

export interface RunInfo {
  run_sk: number;
  model_version: string;
  computed_at: string;
}

export interface TransitionDetail {
  policy: number | null;
  tech: number | null;
  market: number | null;
  carbon_intensity: number | null;
  target_alignment: number | null;
}

export interface ScoreEntry {
  scenario: string;
  horizon_year: number;
  physical: Band | null;
  transition: Band | null;
  composite: Band | null;
  transition_detail: TransitionDetail | null;
  physical_run: RunInfo | null;
  transition_run: RunInfo | null;
  availability?: Availability;
  reason?: string | null;
}

export interface CompanyScores {
  company_sk: number;
  name: string;
  scores: ScoreEntry[];
}

export interface Asset {
  asset_sk: number;
  name: string | null;
  asset_type: string;
  latitude: number | null;
  longitude: number | null;
  municipality: string | null;
  state: string | null;
}

export interface Hazard {
  hazard_type: string;
  scenario: string;
  horizon_year: number;
  exposure_normalized: number;
  run_sk: number;
}

export interface Explanation {
  scenario: string;
  horizon_year: number;
  narrative_md: string;
  drivers: Record<string, unknown> | null;
  run_sk: number;
  computed_at: string;
}

export interface Financial {
  scenario: string;
  horizon_year: number;
  dcf_adjustment_pct: number;
  band_low_pct: number;
  band_high_pct: number;
  run_sk: number;
}

export interface Dossier {
  query: string;
  kind: string;
  status?: DossierStatus;
  name: string | null;
  registry: Record<string, unknown> | null;
  market: DossierMarket | null;
  news: DossierNews;
  controversy_ratio: number | null;
  sources: string[];
  errors: DossierSectionError[];
  fetched_at: string | null;
  cached: boolean;
  company_sk: number | null;
  ibge_code: string | null;
  climate_risk: Record<string, { value: number; label: string }>;
  climate_meta: {
    source?: string;
    scenario?: string;
    horizon?: number;
    municipio?: string;
    uf?: string;
    ibge?: string;
    scale?: string;
  };
  financials: {
    revenue: number | null;
    net_income: number | null;
    ebit?: number | null;
    ebitda?: number | null;
    total_assets?: number | null;
    equity?: number | null;
    gross_debt?: number | null;
    net_margin?: number | null;
    ebitda_margin?: number | null;
    debt_to_ebitda?: number | null;
    roe?: number | null;
    revenue_growth?: number | null;
    history?: {
      fiscal_year: number;
      revenue: number | null;
      ebitda: number | null;
      net_income: number | null;
    }[];
    fiscal_year: number;
    source?: string;
  } | null;
  latitude: number | null;
  longitude: number | null;
  location_label: string | null;
  cross: {
    status?: SectionStatus;
    reason?: string | null;
    climate_index?: { value: number; label: string; basis: string };
    revenue_at_risk?: {
      pct_low: number;
      pct_central: number;
      pct_high: number;
      brl_low: number;
      brl_central: number;
      brl_high: number;
      basis: string;
      seal: string;
    };
    revenue_percentile?: { value: number; n: number; basis: string };
    ebitda_margin_percentile?: { value: number; n: number; basis: string };
    narrative?: string;
  };
  predictions: {
    status?: SectionStatus;
    reason?: string | null;
    segment?: {
      cluster: number;
      label: string;
      n_in_cluster: number;
      n_total: number;
      basis: string;
      seal: string;
    };
    peers?: {
      items: { cnpj: string; denom: string; distance: number }[];
      basis: string;
      seal: string;
    };
    anomaly?: { is_outlier: boolean; score: number; basis: string; seal: string };
  };
  climate_financial: {
    status?: SectionStatus;
    reason?: string | null;
    sector?: {
      cnae: string | null;
      division: string | null;
      archetype: string;
      assumed: boolean;
      sensitivities: { raw_material: number; asset: number; revenue: number; transition: number };
    };
    physical_exposure?: number;
    climate_index?: number;
    channels?: Record<
      string,
      {
        label: string;
        statement: string;
        brl?: { low: number; central: number; high: number };
        pp?: { low: number; central: number; high: number };
        pct_base?: number | null;
      }
    >;
    materialidade?: number;
    risco_ajustado?: { value: number; label: string; basis: string };
    narrative?: string;
    seal?: string;
  };
  relationships?: {
    cnpj?: string;
    gov_supplier?: {
      found: boolean;
      habilitado_licitar?: boolean | null;
      ativo?: boolean | null;
      razao_social?: string | null;
      cnae_nome?: string | null;
      natureza_juridica?: string | null;
      porte?: string | null;
      municipio?: string | null;
      uf?: string | null;
      note?: string;
    } | null;
    socios?: { items: string[]; count: number } | null;
    value_chain?: {
      archetype?: string;
      assumed?: boolean;
      upstream?: { division: string | null; label: string }[];
      downstream?: { division: string | null; label: string }[];
      methodology?: string;
    } | null;
    public_contracts?: { available: boolean; reason?: string };
  } | null;
  supply_chain: {
    status?: SectionStatus;
    reason?: string | null;
    suppliers?: {
      division: string | null;
      label: string;
      archetype?: string | null;
      dominant_hazard: string;
      exposure_index: number;
      fragility: number;
      disruption_index: number;
    }[];
    chain_risk_index?: number;
    dependence_raw_material?: number;
    production_at_risk_brl?: { low: number; central: number; high: number };
    production_at_risk_pct_ebitda?: number | null;
    national_hazard_means?: Record<string, number>;
    methodology?: string;
    narrative?: string;
    seal?: string;
  };
}

export interface Peer {
  company_sk: number;
  name: string;
  distance: number;
}

export interface Anomaly {
  company_sk: number;
  name: string;
  score: number;
  is_outlier: boolean;
}

const REQUEST_TIMEOUT_MS = 30_000;

async function getJson<T>(url: string): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const resp = await fetch(url, { signal: controller.signal });
    if (!resp.ok) {
      let body = "";
      try {
        body = (await resp.text()).slice(0, 300);
      } catch {
        body = "";
      }
      throw new Error(`${resp.status} ${url}${body ? ` — ${body}` : ""}`);
    }
    return (await resp.json()) as T;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error(`timeout após ${REQUEST_TIMEOUT_MS / 1000}s — ${url}`);
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  companies: () => getJson<Company[]>("/v1/companies"),
  scores: (id: number) => getJson<CompanyScores>(`/v1/companies/${id}/scores`),
  assets: (id: number) => getJson<Asset[]>(`/v1/companies/${id}/assets`),
  explanations: (id: number) => getJson<Explanation[]>(`/v1/companies/${id}/explanations`),
  financial: (id: number) => getJson<Financial[]>(`/v1/companies/${id}/financial`),
  hazards: (assetId: number) => getJson<Hazard[]>(`/v1/assets/${assetId}/hazards`),
  search: (q: string) => getJson<Dossier>(`/v1/search?q=${encodeURIComponent(q)}`),
  peers: (id: number) => getJson<Peer[]>(`/v1/companies/${id}/peers`),
  anomaly: (id: number) => getJson<Anomaly | null>(`/v1/companies/${id}/anomaly`),
};
