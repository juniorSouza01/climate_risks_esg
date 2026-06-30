import { useEffect, useMemo, useState } from "react";
import {
  api,
  type Asset,
  type Company,
  type CompanyScores,
  type Explanation,
  type Financial,
  type ScoreEntry,
} from "./api";
import { AssetMap } from "./components/AssetMap";
import { CompareChart, type CompareRow } from "./components/CompareChart";
import { Heatmap } from "./components/Heatmap";
import { Narrative } from "./components/Narrative";
import { ScoreCard } from "./components/ScoreCard";
import { SearchPanel } from "./components/SearchPanel";
import { SubScores } from "./components/SubScores";
import { fmtDate } from "./components/util";

export default function App() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [scoresById, setScoresById] = useState<Record<number, CompanyScores>>({});
  const [assets, setAssets] = useState<Asset[]>([]);
  const [explanations, setExplanations] = useState<Explanation[]>([]);
  const [financial, setFinancial] = useState<Financial[]>([]);
  const [exposureByAsset, setExposureByAsset] = useState<Record<number, number>>({});
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [scenario, setScenario] = useState<string>("");
  const [horizon, setHorizon] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const cs = await api.companies();
        setCompanies(cs);
        if (cs.length > 0) setSelectedId(cs[0].company_sk);
        const entries = await Promise.all(cs.map((c) => api.scores(c.company_sk)));
        const map: Record<number, CompanyScores> = {};
        entries.forEach((e) => {
          map[e.company_sk] = e;
        });
        setScoresById(map);
        const first = entries.flatMap((e) => e.scores)[0];
        if (first) {
          setScenario(first.scenario);
          setHorizon(first.horizon_year);
        }
      } catch (err) {
        setError(String(err));
      }
    })();
  }, []);

  useEffect(() => {
    if (selectedId == null) return;
    api.explanations(selectedId).then(setExplanations).catch(() => setExplanations([]));
    api.financial(selectedId).then(setFinancial).catch(() => setFinancial([]));
    (async () => {
      try {
        const a = await api.assets(selectedId);
        setAssets(a);
        const exposure: Record<number, number> = {};
        await Promise.all(
          a.map(async (asset) => {
            const hz = await api.hazards(asset.asset_sk);
            if (hz.length > 0) {
              exposure[asset.asset_sk] = Math.max(...hz.map((h) => h.exposure_normalized));
            }
          }),
        );
        setExposureByAsset(exposure);
      } catch {
        setAssets([]);
        setExposureByAsset({});
      }
    })();
  }, [selectedId]);

  const scenarios = useMemo(
    () =>
      Array.from(
        new Set(Object.values(scoresById).flatMap((s) => s.scores.map((e) => e.scenario))),
      ),
    [scoresById],
  );
  const horizons = useMemo(
    () =>
      Array.from(
        new Set(Object.values(scoresById).flatMap((s) => s.scores.map((e) => e.horizon_year))),
      ).sort((a, b) => a - b),
    [scoresById],
  );

  const entryFor = (id: number): ScoreEntry | undefined =>
    scoresById[id]?.scores.find((e) => e.scenario === scenario && e.horizon_year === horizon);

  const selected = selectedId != null ? entryFor(selectedId) : undefined;
  const selectedExplanation =
    explanations.find((e) => e.scenario === scenario && e.horizon_year === horizon)
      ?.narrative_md ?? null;
  const selectedFinancial =
    financial.find((f) => f.scenario === scenario && f.horizon_year === horizon) ?? null;

  const compareData: CompareRow[] = companies.map((c) => {
    const e = entryFor(c.company_sk);
    return {
      name: c.name.replace(/ S\.A\.?$/, ""),
      fisico: e?.physical?.central ?? null,
      transicao: e?.transition?.central ?? null,
      composto: e?.composite?.central ?? null,
    };
  });

  const selectedCompany = companies.find((c) => c.company_sk === selectedId);

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1 className="title">
            Climate Risk Intelligence <span className="dot">·</span> ESG
          </h1>
          <p className="subtitle">
            Risco climático físico e de transição por empresa — alinhado a TCFD, ISSB IFRS S2
            e cenários NGFS/IPCC. Score auditável, sempre como banda de incerteza.
          </p>
        </div>
        <div className="badges">
          <span className="badge">CMIP6</span>
          <span className="badge">TCFD</span>
          <span className="badge">ISSB S2</span>
          <span className="badge">NGFS</span>
        </div>
      </header>

      {error && <div className="panel">Falha ao carregar a API: {error}. A API está rodando?</div>}

      <SearchPanel />


      <div className="controls">
        <div className="field">
          <label>Cenário</label>
          <select value={scenario} onChange={(e) => setScenario(e.target.value)}>
            {scenarios.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Horizonte</label>
          <select
            value={horizon ?? ""}
            onChange={(e) => setHorizon(Number(e.target.value))}
          >
            {horizons.map((h) => (
              <option key={h} value={h}>
                {h}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="layout">
        <aside className="company-list">
          {companies.map((c) => {
            const e = entryFor(c.company_sk);
            return (
              <button
                key={c.company_sk}
                className={"company-card" + (c.company_sk === selectedId ? " active" : "")}
                onClick={() => setSelectedId(c.company_sk)}
              >
                <div className="name">{c.name}</div>
                <div className="meta">
                  CNAE {c.sector_nace ?? "—"}
                  {c.ticker ? ` · ${c.ticker}` : ""}
                </div>
                <div className="meta" style={{ marginTop: 6 }}>
                  Composto: {e?.composite ? e.composite.central.toFixed(1) : "—"}
                </div>
                <span className={"pill" + (c.is_listed ? " listed" : "")}>
                  {c.is_listed ? "Capital aberto" : "Capital fechado"}
                </span>
              </button>
            );
          })}
        </aside>

        <main className="main">
          <div className="cards">
            <ScoreCard label="Risco físico" band={selected?.physical ?? null} />
            <ScoreCard label="Risco de transição" band={selected?.transition ?? null} />
            <ScoreCard label="Score composto" band={selected?.composite ?? null} />
          </div>

          {selected && (selected.physical_run || selected.transition_run) && (
            <div className="audit">
              {selected.physical_run && (
                <span>
                  Físico: <code>run #{selected.physical_run.run_sk}</code> · modelo v
                  {selected.physical_run.model_version} · {fmtDate(selected.physical_run.computed_at)}
                </span>
              )}
              {selected.transition_run && (
                <span>
                  Transição: <code>run #{selected.transition_run.run_sk}</code> · v
                  {selected.transition_run.model_version} ·{" "}
                  {fmtDate(selected.transition_run.computed_at)}
                </span>
              )}
            </div>
          )}

          <section className="panel">
            <h3>Explicação do score — {selectedCompany?.name ?? "—"}</h3>
            <Narrative markdown={selectedExplanation} />
          </section>

          <div className="cards">
            <section className="panel">
              <h3>Decomposição do risco de transição</h3>
              <SubScores detail={selected?.transition_detail ?? null} />
            </section>
            <section className="panel">
              <h3>Impacto financeiro projetado (DCF · NGFS)</h3>
              {selectedFinancial ? (
                <div className="fin-grid">
                  <span className="fin-value">{selectedFinancial.dcf_adjustment_pct.toFixed(1)}%</span>
                  <span className="muted">
                    ajuste no valor projetado · faixa {selectedFinancial.band_low_pct.toFixed(1)}% a{" "}
                    {selectedFinancial.band_high_pct.toFixed(1)}%
                  </span>
                </div>
              ) : (
                <div className="muted">Sem projeção financeira neste cenário.</div>
              )}
            </section>
          </div>

          <section className="panel">
            <h3>Ativos de {selectedCompany?.name ?? "—"} (cor = exposição a hazard)</h3>
            <AssetMap assets={assets} exposureByAsset={exposureByAsset} />
          </section>

          <section className="panel">
            <h3>Heatmap da carteira — cenário {scenario}</h3>
            <Heatmap
              companies={companies}
              scoresById={scoresById}
              scenario={scenario}
              horizons={horizons}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          </section>

          <section className="panel">
            <h3>
              Comparativo da carteira — {scenario} · {horizon ?? "—"}
            </h3>
            <CompareChart data={compareData} />
          </section>
        </main>
      </div>

      <footer className="footer">
        Plataforma de Análise de Riscos Climáticos para ESG · dados CMIP6 EC-Earth3 · scores com
        linhagem auditável (run_sk). Protótipo — valores físicos baseados em climatologia
        histórica; cenários SSP e índices xclim em evolução.
      </footer>
    </div>
  );
}
