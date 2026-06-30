export interface Company {
  company_sk: number;
  name: string;
  ticker: string | null;
  sector_nace: string | null;
  is_listed: boolean;
}

export interface Band {
  central: number;
  low: number;
  high: number;
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
  name: string | null;
  registry: Record<string, unknown> | null;
  market: Record<string, unknown> | null;
  news: { title: string; url: string; domain: string; seendate: string }[];
  controversy_ratio: number;
  sources: string[];
  errors: string[];
  fetched_at: string | null;
  cached: boolean;
  company_sk: number | null;
  ibge_code: string | null;
  climate_risk: Record<string, { value: number; label: string }>;
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

async function getJson<T>(url: string): Promise<T> {
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`${resp.status} ${url}`);
  }
  return (await resp.json()) as T;
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
