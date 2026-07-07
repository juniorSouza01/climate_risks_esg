import type { Dossier, SectionStatus } from "../api";
import { Narrative } from "./Narrative";
import { fmtBRL, severityColor } from "./util";

const SEAL_STYLE: Record<string, { bg: string; label: string }> = {
  factual: { bg: "#166534", label: "FACTUAL" },
  inferido: { bg: "#854d0e", label: "INFERIDO" },
  previsto: { bg: "#1e3a8a", label: "PREVISTO" },
};

export function Seal({ kind }: { kind?: string }) {
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

const CHANNEL_ORDER = ["receita", "materia_prima", "ebitda", "ativos", "roi"];

function isBlocked(status?: SectionStatus): boolean {
  return status != null && status !== "ok";
}

function SectionNotice({ title, reason }: { title: string; reason?: string | null }) {
  return (
    <section className="sub-panel">
      <h4>{title}</h4>
      <div className="muted">{reason || "Seção indisponível para esta empresa."}</div>
    </section>
  );
}

export function CompanyAnalytics({ dossier }: { dossier: Dossier }) {
  const c = dossier.cross ?? {};
  const p = dossier.predictions ?? {};
  const cf = dossier.climate_financial ?? {};
  const sc = dossier.supply_chain ?? {};
  const cfBlocked = isBlocked(cf.status);
  const scBlocked = isBlocked(sc.status);
  const predBlocked = isBlocked(p.status);
  const crossBlocked = isBlocked(c.status);
  const hasCross =
    !crossBlocked && (c.climate_index || c.revenue_at_risk || c.revenue_percentile);
  const hasPred = !predBlocked && (p.segment || p.peers || p.anomaly);
  const hasCF = !cfBlocked && cf.channels && cf.risco_ajustado;
  const hasSC = !scBlocked && (sc.suppliers?.length ?? 0) > 0;
  if (
    !hasCross &&
    !hasPred &&
    !hasCF &&
    !hasSC &&
    !cfBlocked &&
    !scBlocked &&
    !predBlocked &&
    !crossBlocked
  ) {
    return null;
  }

  const ci = c.climate_index;
  const rar = c.revenue_at_risk;
  const rp = c.revenue_percentile;
  const emp = c.ebitda_margin_percentile;

  return (
    <>
      {crossBlocked && <SectionNotice title="Cruzamento de dados" reason={c.reason} />}
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
                <div className="cross-val" style={{ color: severityColor(ci.value ?? 0) }}>
                  {ci.value?.toFixed(0) ?? "—"}/100 · {ci.label}
                </div>
                <Bar value={ci.value ?? 0} color={severityColor(ci.value ?? 0)} />
              </div>
            )}
            {rar && (
              <div className="cross-card">
                <div className="cross-top">
                  <span>Receita-em-risco climático</span>
                  <Seal kind="inferido" />
                </div>
                <div className="cross-val" style={{ color: "#f59e0b" }}>
                  {rar.pct_central?.toFixed(1) ?? "—"}% · {fmtBRL(rar.brl_central)}
                </div>
                <div className="muted">
                  faixa {rar.pct_low?.toFixed(1) ?? "—"}–{rar.pct_high?.toFixed(1) ?? "—"}% ·
                  heurística, não perda modelada
                </div>
              </div>
            )}
            {rp && (
              <div className="cross-card">
                <div className="cross-top">
                  <span>Receita no setor</span>
                  <Seal kind="factual" />
                </div>
                <div className="cross-val">percentil {rp.value?.toFixed(0) ?? "—"}</div>
                <Bar value={rp.value ?? 0} color="#38bdf8" />
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
                <div className="cross-val">percentil {emp.value?.toFixed(0) ?? "—"}</div>
                <Bar value={emp.value ?? 0} color="#38bdf8" />
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

      {cfBlocked && (
        <SectionNotice title="Impacto financeiro do risco climático" reason={cf.reason} />
      )}
      {hasCF && (
        <section className="sub-panel cross">
          <h4>
            Impacto financeiro do risco climático <Seal kind={cf.seal} />
          </h4>
          <p className="muted" style={{ marginTop: -4 }}>
            Traduz a ameaça climática da sede em impacto no DRE, balanço e retorno, ponderado pelo
            modelo de negócio (setor <b>{cf.sector?.archetype}</b>
            {cf.sector?.assumed ? " · setor assumido pelo cadastro" : ""}). Coeficientes setoriais
            calibráveis — estimativa, não perda modelada por ativo.
          </p>

          {cf.risco_ajustado && (
            <div className="cross-card" style={{ marginBottom: 12 }}>
              <div className="cross-top">
                <span>Risco climático ajustado pela materialidade financeira</span>
              </div>
              <div className="cross-val" style={{ color: severityColor(cf.risco_ajustado.value ?? 0) }}>
                {cf.risco_ajustado.value?.toFixed(0) ?? "—"}/100 · {cf.risco_ajustado.label}
              </div>
              <Bar
                value={cf.risco_ajustado.value ?? 0}
                color={severityColor(cf.risco_ajustado.value ?? 0)}
              />
              <div className="muted">
                clima da sede {cf.climate_index?.toFixed(0)}/100 × materialidade{" "}
                {((cf.materialidade ?? 0) * 100).toFixed(0)}% do EBITDA exposto → o risco cresce com
                o impacto financeiro.
              </div>
            </div>
          )}

          <div className="cross-grid">
            {CHANNEL_ORDER.filter((k) => cf.channels?.[k]).map((k) => {
              const ch = cf.channels?.[k];
              if (!ch) return null;
              const isRoi = !!ch.pp;
              const band = ch.pp ?? ch.brl;
              if (!band) return null;
              return (
                <div key={k} className="cross-card">
                  <div className="cross-top">
                    <span>{ch.label}</span>
                    <span className="seal" style={{ background: "#334155" }}>
                      {ch.statement}
                    </span>
                  </div>
                  <div className="cross-val" style={{ color: "#f59e0b" }}>
                    {isRoi ? `−${band.central?.toFixed(2) ?? "—"} p.p.` : fmtBRL(band.central)}
                  </div>
                  <div className="muted">
                    faixa{" "}
                    {isRoi
                      ? `${band.low?.toFixed(2) ?? "—"}–${band.high?.toFixed(2) ?? "—"} p.p.`
                      : `${fmtBRL(band.low)} – ${fmtBRL(band.high)}`}
                    {ch.pct_base != null ? ` · ${ch.pct_base}% da linha` : ""}
                  </div>
                </div>
              );
            })}
          </div>

          {cf.narrative && (
            <div className="result-block">
              <Narrative markdown={cf.narrative} />
            </div>
          )}
        </section>
      )}

      {scBlocked && (
        <SectionNotice title="Risco climático na cadeia de suprimentos" reason={sc.reason} />
      )}
      {hasSC && (
        <section className="sub-panel cross">
          <h4>
            Risco climático na cadeia de suprimentos <Seal kind={sc.seal} />
          </h4>
          <p className="muted" style={{ marginTop: -4 }}>
            Se um fornecedor sofre um evento climático (ex.: seca destrói a safra de algodão), a
            produção para e a empresa perde dinheiro. Setores fornecedores típicos do CNAE ×
            exposição climática média nacional (AdaptaBrasil) — não são fornecedores reais.
          </p>

          <div className="cross-grid">
            <div className="cross-card">
              <div className="cross-top">
                <span>Índice de risco da cadeia</span>
              </div>
              <div
                className="cross-val"
                style={{ color: severityColor(sc.chain_risk_index ?? 0) }}
              >
                {(sc.chain_risk_index ?? 0).toFixed(0)}/100
              </div>
              <Bar
                value={sc.chain_risk_index ?? 0}
                color={severityColor(sc.chain_risk_index ?? 0)}
              />
            </div>
            {sc.production_at_risk_brl && (
              <div className="cross-card">
                <div className="cross-top">
                  <span>Perda de produção potencial</span>
                </div>
                <div className="cross-val" style={{ color: "#f59e0b" }}>
                  {fmtBRL(sc.production_at_risk_brl?.central)}
                  {sc.production_at_risk_pct_ebitda != null
                    ? ` · ${sc.production_at_risk_pct_ebitda.toFixed(0)}% do EBITDA`
                    : ""}
                </div>
                <div className="muted">
                  faixa {fmtBRL(sc.production_at_risk_brl?.low)} –{" "}
                  {fmtBRL(sc.production_at_risk_brl?.high)} · dependência de insumos{" "}
                  {((sc.dependence_raw_material ?? 0) * 100).toFixed(0)}%
                </div>
              </div>
            )}
          </div>

          <div className="cross-grid" style={{ marginTop: 12 }}>
            {(sc.suppliers ?? []).map((s, i) => (
              <div key={i} className="cross-card">
                <div className="cross-top">
                  <span>{s.label}</span>
                </div>
                <div
                  className="cross-val"
                  style={{ fontSize: 16, color: severityColor(s.disruption_index ?? 0) }}
                >
                  disrupção {s.disruption_index?.toFixed(0) ?? "—"}/100
                </div>
                <Bar
                  value={s.disruption_index ?? 0}
                  color={severityColor(s.disruption_index ?? 0)}
                />
                <div className="muted">
                  ameaça dominante: <b>{s.dominant_hazard}</b> · exposição{" "}
                  {s.exposure_index?.toFixed(0) ?? "—"}/100
                </div>
              </div>
            ))}
          </div>

          {sc.narrative && (
            <div className="result-block">
              <Narrative markdown={sc.narrative} />
            </div>
          )}
        </section>
      )}

      {predBlocked && <SectionNotice title="Análises preditivas (ML)" reason={p.reason} />}
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
                  score {p.anomaly.score?.toFixed(3) ?? "—"} · {p.anomaly.basis}
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
