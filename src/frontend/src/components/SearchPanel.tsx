import { useState } from "react";
import { api, type Anomaly, type Dossier, type Financial, type Peer } from "../api";

function fmtNum(v: unknown): string {
  if (typeof v !== "number") return "—";
  if (Math.abs(v) >= 1e9) return (v / 1e9).toFixed(1) + " bi";
  if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(1) + " mi";
  return v.toLocaleString("pt-BR");
}

export function SearchPanel() {
  const [q, setQ] = useState("");
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [peers, setPeers] = useState<Peer[]>([]);
  const [anomaly, setAnomaly] = useState<Anomaly | null>(null);
  const [financial, setFinancial] = useState<Financial[]>([]);
  const [loading, setLoading] = useState(false);

  async function run(e: React.FormEvent) {
    e.preventDefault();
    if (q.trim().length < 2) return;
    setLoading(true);
    try {
      const d = await api.search(q.trim());
      setDossier(d);
      if (d.company_sk != null) {
        const [p, a, f] = await Promise.all([
          api.peers(d.company_sk),
          api.anomaly(d.company_sk),
          api.financial(d.company_sk),
        ]);
        setPeers(p);
        setAnomaly(a);
        setFinancial(f);
      } else {
        setPeers([]);
        setAnomaly(null);
        setFinancial([]);
      }
    } catch {
      setDossier(null);
    } finally {
      setLoading(false);
    }
  }

  const reg = dossier?.registry as Record<string, unknown> | null;
  const mkt = dossier?.market as Record<string, unknown> | null;
  const lastFin = financial[0];

  return (
    <section className="panel">
      <h3>Buscar empresa — CNPJ, ticker ou nome</h3>
      <form onSubmit={run} className="search-form">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Ex.: SHUL4 · 84.693.183/0001-68 · Vale"
        />
        <button type="submit" disabled={loading}>
          {loading ? "Buscando…" : "Buscar"}
        </button>
      </form>

      {dossier && (
        <div className="search-result">
          <div className="result-head">
            <span className="result-name">{dossier.name}</span>
            <span className="badge">{dossier.kind}</span>
            {dossier.cached && <span className="badge">cache</span>}
            {dossier.sources.map((s) => (
              <span key={s} className="pill">
                {s}
              </span>
            ))}
          </div>

          <div className="chips">
            {reg?.cnae != null && (
              <span className="chip-metric">
                CNAE<b>{String(reg.cnae).slice(0, 40)}</b>
              </span>
            )}
            {reg?.situacao != null && (
              <span className="chip-metric">
                Situação<b>{String(reg.situacao)}</b>
              </span>
            )}
            {reg?.municipio != null && (
              <span className="chip-metric">
                Sede<b>
                  {String(reg.municipio)}/{String(reg.uf ?? "")}
                </b>
              </span>
            )}
            {mkt?.price != null && (
              <span className="chip-metric">
                Preço<b>R$ {fmtNum(mkt.price)}</b>
              </span>
            )}
            {mkt?.market_cap != null && (
              <span className="chip-metric">
                Market cap<b>{fmtNum(mkt.market_cap)}</b>
              </span>
            )}
            {mkt?.annualized_volatility != null && (
              <span className="chip-metric">
                Volatilidade<b>{(Number(mkt.annualized_volatility) * 100).toFixed(0)}%</b>
              </span>
            )}
            {lastFin && (
              <span className="chip-metric">
                Impacto climático (DCF)<b>{lastFin.dcf_adjustment_pct.toFixed(1)}%</b>
              </span>
            )}
            <span className="chip-metric">
              Controvérsia (notícias)<b>{(dossier.controversy_ratio * 100).toFixed(0)}%</b>
            </span>
            {anomaly && (
              <span className="chip-metric">
                Anomalia<b style={{ color: anomaly.is_outlier ? "#ef4444" : "#22c55e" }}>
                  {anomaly.is_outlier ? "atípica" : "normal"}
                </b>
              </span>
            )}
          </div>

          {Object.keys(dossier.climate_risk).length > 0 && (
            <div className="result-block">
              <div className="muted">
                Risco climático municipal — AdaptaBrasil (SSP5-8.5, 2050):
              </div>
              <div className="chips">
                {Object.entries(dossier.climate_risk).map(([hazard, r]) => (
                  <span key={hazard} className="chip-metric">
                    {hazard}
                    <b
                      style={{
                        color:
                          r.value < 0.33 ? "#22c55e" : r.value < 0.66 ? "#f59e0b" : "#ef4444",
                      }}
                    >
                      {(r.value * 100).toFixed(0)} · {r.label}
                    </b>
                  </span>
                ))}
              </div>
            </div>
          )}

          {peers.length > 0 && (
            <div className="result-block">
              <div className="muted">Pares (similaridade ML):</div>
              <div className="peer-list">
                {peers.map((p) => (
                  <span key={p.company_sk} className="pill">
                    {p.name.replace(/ S\.?A\.?$/, "")}
                  </span>
                ))}
              </div>
            </div>
          )}

          {dossier.news.length > 0 && (
            <div className="result-block">
              <div className="muted">Notícias recentes ({dossier.news.length}):</div>
              <ul className="news-list">
                {dossier.news.slice(0, 6).map((n, i) => (
                  <li key={i}>
                    <a href={n.url} target="_blank" rel="noreferrer">
                      {n.title || n.domain}
                    </a>
                    <span className="muted"> · {n.domain}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {dossier.errors.length > 0 && (
            <div className="muted">fontes indisponíveis: {dossier.errors.join("; ")}</div>
          )}
          {dossier.company_sk == null && (
            <div className="muted">
              Empresa fora da base interna — sem peers/anomalia (busca externa apenas).
            </div>
          )}
        </div>
      )}
    </section>
  );
}
