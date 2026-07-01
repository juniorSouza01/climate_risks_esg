import type { Dossier } from "../api";
import { Narrative } from "./Narrative";

function fmtBRL(v: number): string {
  if (Math.abs(v) >= 1e9) return "R$ " + (v / 1e9).toFixed(2) + " bi";
  if (Math.abs(v) >= 1e6) return "R$ " + (v / 1e6).toFixed(2) + " mi";
  if (Math.abs(v) >= 1e3) return "R$ " + (v / 1e3).toFixed(0) + " mil";
  return "R$ " + v.toFixed(0);
}

const SEAL_STYLE: Record<string, { bg: string; label: string }> = {
  factual: { bg: "#166534", label: "FACTUAL" },
  inferido: { bg: "#854d0e", label: "INFERIDO" },
  previsto: { bg: "#1e3a8a", label: "PREVISTO" },
};

function Seal({ kind }: { kind?: string }) {
  const s = SEAL_STYLE[kind ?? ""] ?? { bg: "#334155", label: (kind ?? "").toUpperCase() };
  return (
    <span className="seal" style={{ background: s.bg }}>
      {s.label}
    </span>
  );
}

function Bar({ value, color }: { value: number; color: string }) {
  return (
    <div className="pct-track">
      <div className="pct-fill" style={{ width: `${Math.max(0, Math.min(100, value))}%`, background: color }} />
    </div>
  );
}

export function CompanyAnalytics({ dossier }: { dossier: Dossier }) {
  const c = dossier.cross ?? {};
  const p = dossier.predictions ?? {};
  const hasCross = c.climate_index || c.revenue_at_risk || c.revenue_percentile;
  const hasPred = p.segment || p.peers || p.anomaly;
  if (!hasCross && !hasPred) return null;

  const ci = c.climate_index;
  const rar = c.revenue_at_risk;
  const rp = c.revenue_percentile;
  const emp = c.ebitda_margin_percentile;

  return (
    <>
      {hasCross && (
        <section className="sub-panel cross">
          <h4>Cruzamento de dados</h4>
          <p className="muted" style={{ marginTop: -4 }}>
            Combina clima × financeiro × mercado numa leitura única. Índices comparados ao universo
            de cias abertas da CVM.
          </p>
          <div className="cross-grid">
            {ci && (
              <div className="cross-card">
                <div className="cross-top">
                  <span>Ameaça climática (sede)</span>
                  <Seal kind="factual" />
                </div>
                <div className="cross-val" style={{ color: ci.value < 33 ? "#22c55e" : ci.value < 66 ? "#f59e0b" : "#ef4444" }}>
                  {ci.value.toFixed(0)}/100 · {ci.label}
                </div>
                <Bar value={ci.value} color={ci.value < 33 ? "#22c55e" : ci.value < 66 ? "#f59e0b" : "#ef4444"} />
              </div>
            )}
            {rar && (
              <div className="cross-card">
                <div className="cross-top">
                  <span>Receita-em-risco climático</span>
                  <Seal kind="inferido" />
                </div>
                <div className="cross-val" style={{ color: "#f59e0b" }}>
                  {rar.pct_central.toFixed(1)}% · {fmtBRL(rar.brl_central)}
                </div>
                <div className="muted">
                  faixa {rar.pct_low.toFixed(1)}–{rar.pct_high.toFixed(1)}% · heurística, não perda
                  modelada
                </div>
              </div>
            )}
            {rp && (
              <div className="cross-card">
                <div className="cross-top">
                  <span>Receita no setor</span>
                  <Seal kind="factual" />
                </div>
                <div className="cross-val">percentil {rp.value.toFixed(0)}</div>
                <Bar value={rp.value} color="#38bdf8" />
                <div className="muted">
                  de {rp.n} cias · {rp.basis}
                </div>
              </div>
            )}
            {emp && (
              <div className="cross-card">
                <div className="cross-top">
                  <span>Margem EBITDA</span>
                  <Seal kind="factual" />
                </div>
                <div className="cross-val">percentil {emp.value.toFixed(0)}</div>
                <Bar value={emp.value} color="#38bdf8" />
                <div className="muted">de {emp.n} cias · {emp.basis}</div>
              </div>
            )}
          </div>
          {c.narrative && (
            <div className="result-block">
              <Narrative markdown={c.narrative} />
            </div>
          )}
        </section>
      )}

      {hasPred && (
        <section className="sub-panel analysis">
          <h4>Análises preditivas (ML)</h4>
          <p className="muted" style={{ marginTop: -4 }}>
            Modelos treinados on-the-fly sobre o universo de cias abertas da CVM (~466 empresas).
          </p>
          <div className="report-grid">
            {p.segment && (
              <div className="pred-card">
                <div className="cross-top">
                  <span>Segmentação (K-Means)</span>
                  <Seal kind={p.segment.seal} />
                </div>
                <div className="cross-val">{p.segment.label}</div>
                <div className="muted">
                  cluster {p.segment.cluster} · {p.segment.n_in_cluster}/{p.segment.n_total}{" "}
                  empresas · {p.segment.basis}
                </div>
              </div>
            )}
            {p.anomaly && (
              <div className="pred-card">
                <div className="cross-top">
                  <span>Detecção de anomalia</span>
                  <Seal kind={p.anomaly.seal} />
                </div>
                <div
                  className="cross-val"
                  style={{ color: p.anomaly.is_outlier ? "#ef4444" : "#22c55e" }}
                >
                  {p.anomaly.is_outlier ? "Perfil atípico" : "Perfil típico"}
                </div>
                <div className="muted">
                  score {p.anomaly.score.toFixed(3)} · {p.anomaly.basis}
                </div>
              </div>
            )}
          </div>
          {p.peers && p.peers.items.length > 0 && (
            <div className="result-block">
              <div className="muted" style={{ marginBottom: 6 }}>
                Pares por perfil financeiro (receita/margens):
              </div>
              <div className="peer-list">
                {p.peers.items.map((peer) => (
                  <span key={peer.cnpj} className="pill">
                    {peer.denom.replace(/ S\.?A\.?$/, "")}
                    <small> · {peer.distance.toFixed(2)}</small>
                  </span>
                ))}
              </div>
            </div>
          )}
        </section>
      )}
    </>
  );
}
