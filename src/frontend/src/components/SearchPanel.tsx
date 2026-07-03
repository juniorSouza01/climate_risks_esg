import { useMemo, useState } from "react";
import {
  api,
  type Anomaly,
  type CompanyScores,
  type Dossier,
  type Explanation,
  type Financial,
  type Peer,
  type ScoreEntry,
} from "../api";
import { CompanyAnalytics } from "./CompanyAnalytics";
import { MiniLocationMap } from "./MiniLocationMap";
import { Narrative } from "./Narrative";
import { Relationships } from "./Relationships";
import { ScoreCard } from "./ScoreCard";
import { SubScores } from "./SubScores";

const SOURCE_LABEL: Record<string, string> = {
  brasilapi: "Cadastro · BrasilAPI",
  brapi: "Mercado · B3/brapi",
  gdelt: "Notícias · GDELT",
  adaptabrasil: "Clima · AdaptaBrasil",
  cvm: "Financeiro · CVM",
};

const HAZARD_DESC: Record<string, string> = {
  enchente: "Inundações e cheias urbanas",
  deslizamento: "Movimento de massa em encostas",
  vendaval: "Ventos intensos e tempestades",
  seca: "Estiagem e escassez hídrica",
};

function fmtNum(v: unknown): string {
  if (typeof v !== "number" || Number.isNaN(v)) return "—";
  if (Math.abs(v) >= 1e9) return (v / 1e9).toFixed(2) + " bi";
  if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(2) + " mi";
  return v.toLocaleString("pt-BR");
}

function fmtMoney(v: unknown): string {
  const n = typeof v === "string" ? Number(v) : v;
  if (typeof n !== "number" || Number.isNaN(n)) return "—";
  return "R$ " + fmtNum(n);
}

function riskColor(v: number): string {
  return v < 33 ? "#22c55e" : v < 66 ? "#f59e0b" : "#ef4444";
}

function friendlyError(e: string): string {
  const src = e.split(":")[0].trim();
  return `${SOURCE_LABEL[src] ?? src} indisponível no momento`;
}

function pickDefault(entries: ScoreEntry[]): { scenario: string; horizon: number } | null {
  if (!entries.length) return null;
  const withBand = entries.filter((e) => e.physical || e.transition || e.composite);
  const pool = withBand.length ? withBand : entries;
  const pref =
    pool.find((e) => /SSP5/i.test(e.scenario) && e.horizon_year === 2050) ??
    pool.find((e) => /SSP5/i.test(e.scenario)) ??
    pool[0];
  return { scenario: pref.scenario, horizon: pref.horizon_year };
}

function S(v: unknown): string {
  return v == null || v === "" ? "—" : String(v);
}

export function SearchPanel() {
  const [q, setQ] = useState("");
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [scores, setScores] = useState<CompanyScores | null>(null);
  const [explanations, setExplanations] = useState<Explanation[]>([]);
  const [peers, setPeers] = useState<Peer[]>([]);
  const [anomaly, setAnomaly] = useState<Anomaly | null>(null);
  const [financial, setFinancial] = useState<Financial[]>([]);
  const [scenario, setScenario] = useState("");
  const [horizon, setHorizon] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  function reset() {
    setScores(null);
    setExplanations([]);
    setPeers([]);
    setAnomaly(null);
    setFinancial([]);
    setScenario("");
    setHorizon(null);
  }

  async function run(e: React.FormEvent) {
    e.preventDefault();
    if (q.trim().length < 2) return;
    setLoading(true);
    reset();
    try {
      const d = await api.search(q.trim());
      setDossier(d);
      if (d.company_sk != null) {
        const sk = d.company_sk;
        const [sc, ex, p, a, f] = await Promise.all([
          api.scores(sk).catch(() => null),
          api.explanations(sk).catch(() => []),
          api.peers(sk).catch(() => []),
          api.anomaly(sk).catch(() => null),
          api.financial(sk).catch(() => []),
        ]);
        setScores(sc);
        setExplanations(ex);
        setPeers(p);
        setAnomaly(a);
        setFinancial(f);
        const def = pickDefault(sc?.scores ?? []);
        if (def) {
          setScenario(def.scenario);
          setHorizon(def.horizon);
        }
      }
    } catch {
      setDossier(null);
    } finally {
      setLoading(false);
    }
  }

  const reg = (dossier?.registry ?? {}) as Record<string, unknown>;
  const mkt = (dossier?.market ?? null) as Record<string, unknown> | null;
  const fin = dossier?.financials ?? null;
  const cm = dossier?.climate_meta ?? {};

  const scenarios = useMemo(
    () => Array.from(new Set((scores?.scores ?? []).map((e) => e.scenario))),
    [scores],
  );
  const horizons = useMemo(
    () =>
      Array.from(new Set((scores?.scores ?? []).map((e) => e.horizon_year))).sort((a, b) => a - b),
    [scores],
  );
  const entry =
    scores?.scores.find((e) => e.scenario === scenario && e.horizon_year === horizon) ?? null;
  const narrative =
    explanations.find((e) => e.scenario === scenario && e.horizon_year === horizon)?.narrative_md ??
    null;
  const finEntry =
    financial.find((f) => f.scenario === scenario && f.horizon_year === horizon) ?? null;

  const addressLine = [reg.logradouro, reg.numero, reg.complemento, reg.bairro]
    .filter((x) => x != null && x !== "")
    .map(String)
    .join(", ");

  const netMargin =
    fin?.net_margin != null
      ? fin.net_margin * 100
      : fin && fin.revenue && fin.net_income
        ? (fin.net_income / fin.revenue) * 100
        : null;
  const ebitdaMargin = fin?.ebitda_margin != null ? fin.ebitda_margin * 100 : null;
  const brapiErr = dossier?.errors.some((e) => e.startsWith("brapi")) ?? false;

  return (
    <section className="panel">
      <h3>Inteligência por empresa — busque por CNPJ, ticker ou nome</h3>
      <form onSubmit={run} className="search-form">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Ex.: SHUL4 · 84.693.183/0001-68 · Vale · Döhler"
        />
        <button type="submit" disabled={loading}>
          {loading ? "Analisando…" : "Analisar"}
        </button>
      </form>

      {dossier && (
        <div className="report">
          <div className="report-head">
            <div>
              <div className="report-name">{dossier.name}</div>
              <div className="report-sub">
                {reg.razao_social ? S(reg.razao_social) : `consulta: ${dossier.query}`}
              </div>
            </div>
            <div className="report-tags">
              <span className="badge">{dossier.kind}</span>
              {dossier.cached && <span className="badge">cache</span>}
              {dossier.sources.map((s) => (
                <span key={s} className="pill listed">
                  {SOURCE_LABEL[s] ?? s}
                </span>
              ))}
            </div>
          </div>

          <div className="kpi-strip">
            <Kpi label="Situação cadastral" value={S(reg.situacao)} />
            <Kpi label="Porte" value={S(reg.porte)} />
            {mkt?.market_cap != null && <Kpi label="Market cap" value={fmtNum(mkt.market_cap)} />}
            {mkt?.annualized_volatility != null && (
              <Kpi
                label="Volatilidade anual"
                value={`${(Number(mkt.annualized_volatility) * 100).toFixed(0)}%`}
              />
            )}
            {fin?.revenue != null && (
              <Kpi label={`Receita CVM ${fin.fiscal_year}`} value={fmtMoney(fin.revenue)} />
            )}
            {fin?.ebitda != null && <Kpi label="EBITDA" value={fmtMoney(fin.ebitda)} />}
            <Kpi
              label="Controvérsia (notícias)"
              value={`${(dossier.controversy_ratio * 100).toFixed(0)}%`}
            />
            {anomaly && (
              <Kpi
                label="Perfil (ML)"
                value={anomaly.is_outlier ? "atípico" : "típico"}
                color={anomaly.is_outlier ? "#ef4444" : "#22c55e"}
              />
            )}
          </div>

          <div className="report-grid">
            <section className="sub-panel">
              <h4>Identificação</h4>
              <dl className="kv">
                <Kv k="CNPJ" v={S(reg.cnpj)} />
                <Kv k="Razão social" v={S(reg.razao_social)} />
                <Kv k="Nome fantasia" v={S(reg.nome_fantasia)} />
                <Kv
                  k="CNAE principal"
                  v={reg.cnae ? `${S(reg.cnae_codigo)} · ${S(reg.cnae)}` : "—"}
                />
                {Array.isArray(reg.cnaes_secundarios) && reg.cnaes_secundarios.length > 0 && (
                  <Kv
                    k={`CNAEs secundários (${reg.cnaes_secundarios.length})`}
                    v={(reg.cnaes_secundarios as { codigo: number; descricao: string }[])
                      .slice(0, 6)
                      .map((c) => c.descricao)
                      .join(" · ")}
                  />
                )}
                <Kv k="Natureza jurídica" v={S(reg.natureza_juridica)} />
                <Kv k="Capital social" v={fmtMoney(reg.capital_social)} />
                <Kv k="Início de atividade" v={S(reg.data_inicio_atividade)} />
                {Array.isArray(reg.socios) && reg.socios.length > 0 && (
                  <Kv k="Sócios (QSA)" v={(reg.socios as string[]).join(" · ")} />
                )}
              </dl>
            </section>

            <section className="sub-panel locate">
              <h4>📍 Localização</h4>
              {addressLine || reg.municipio ? (
                <>
                  <div className="addr">{addressLine || "—"}</div>
                  <div className="addr-city">
                    {S(reg.municipio)}
                    {reg.uf ? `/${S(reg.uf)}` : ""} {reg.cep ? `· CEP ${S(reg.cep)}` : ""}
                  </div>
                  <dl className="kv">
                    <Kv k="Telefone" v={S(reg.telefone)} />
                    <Kv k="Código IBGE" v={S(dossier.ibge_code)} />
                  </dl>
                  {dossier.latitude != null && dossier.longitude != null && (
                    <MiniLocationMap
                      lat={dossier.latitude}
                      lon={dossier.longitude}
                      label={dossier.location_label}
                    />
                  )}
                  {dossier.ibge_code && (
                    <div className="muted">
                      É este município que define o risco climático abaixo.
                    </div>
                  )}
                </>
              ) : (
                <div className="muted">
                  Sem endereço cadastral (busca por ticker/nome não retorna CNPJ).
                </div>
              )}
            </section>

            <section className="sub-panel">
              <h4>Mercado · B3</h4>
              {mkt ? (
                <dl className="kv">
                  <Kv k="Ticker" v={S(mkt.ticker)} />
                  <Kv k="Preço" v={mkt.price != null ? `R$ ${fmtNum(mkt.price)}` : "—"} />
                  <Kv k="Market cap" v={fmtMoney(mkt.market_cap)} />
                  <Kv k="P/L" v={mkt.pe_ratio != null ? Number(mkt.pe_ratio).toFixed(1) : "—"} />
                  <Kv
                    k="Volatilidade (anual)"
                    v={
                      mkt.annualized_volatility != null
                        ? `${(Number(mkt.annualized_volatility) * 100).toFixed(1)}%`
                        : "— (requer plano pago)"
                    }
                  />
                </dl>
              ) : brapiErr ? (
                <div className="muted">
                  Mercado B3 indisponível no momento (limite de requisições da brapi) — tente
                  novamente em instantes.
                </div>
              ) : (
                <div className="muted">
                  Empresa não listada na B3 (ou sem ticker associado) — sem dados de mercado.
                </div>
              )}
            </section>

            <section className="sub-panel">
              <h4>Financeiro · CVM (DFP)</h4>
              {fin ? (
                <dl className="kv">
                  <Kv k="Ano fiscal" v={S(fin.fiscal_year)} />
                  <Kv k="Receita líquida" v={fin.revenue != null ? fmtMoney(fin.revenue) : "—"} />
                  <Kv k="EBITDA" v={fin.ebitda != null ? fmtMoney(fin.ebitda) : "—"} />
                  <Kv
                    k="Margem EBITDA"
                    v={ebitdaMargin != null ? `${ebitdaMargin.toFixed(1)}%` : "—"}
                  />
                  <Kv k="EBIT (operacional)" v={fin.ebit != null ? fmtMoney(fin.ebit) : "—"} />
                  <Kv
                    k="Lucro líquido"
                    v={fin.net_income != null ? fmtMoney(fin.net_income) : "—"}
                  />
                  <Kv k="Margem líquida" v={netMargin != null ? `${netMargin.toFixed(1)}%` : "—"} />
                  <Kv
                    k="Crescimento receita"
                    v={
                      fin.revenue_growth != null
                        ? `${(fin.revenue_growth * 100).toFixed(1)}% a/a`
                        : "—"
                    }
                  />
                  <Kv
                    k="Ativos totais"
                    v={fin.total_assets != null ? fmtMoney(fin.total_assets) : "—"}
                  />
                  <Kv
                    k="Patrimônio líquido"
                    v={fin.equity != null ? fmtMoney(fin.equity) : "—"}
                  />
                  <Kv
                    k="Dívida bruta"
                    v={fin.gross_debt != null ? fmtMoney(fin.gross_debt) : "—"}
                  />
                  <Kv
                    k="Dívida/EBITDA"
                    v={fin.debt_to_ebitda != null ? `${fin.debt_to_ebitda.toFixed(1)}×` : "—"}
                  />
                  <Kv
                    k="ROE"
                    v={fin.roe != null ? `${(fin.roe * 100).toFixed(1)}%` : "—"}
                  />
                  <Kv k="Fonte" v={`CVM DFP · ${S(fin.source)}`} />
                </dl>
              ) : (
                <div className="muted">
                  Sem demonstrativo (DFP) na CVM para esta empresa — comum em empresas de capital
                  fechado ou não casadas por nome.
                </div>
              )}
            </section>
          </div>

          <section className="sub-panel climate">
            <h4>Risco climático municipal</h4>
            {Object.keys(dossier.climate_risk).length > 0 ? (
              <>
                <p className="explain">
                  Índice do <b>{S(cm.source) || "AdaptaBrasil"}</b> — é uma ameaça{" "}
                  <b>municipal</b> de {S(cm.municipio)}/{S(cm.uf)} (IBGE {S(cm.ibge)}), não da
                  empresa isolada. Cenário <b>{S(cm.scenario)}</b> · horizonte{" "}
                  <b>{S(cm.horizon)}</b>. Escala 0–100:{" "}
                  <span style={{ color: "#22c55e" }}>até 33 baixo</span> ·{" "}
                  <span style={{ color: "#f59e0b" }}>33–66 médio</span> ·{" "}
                  <span style={{ color: "#ef4444" }}>acima de 66 alto</span>.
                </p>
                <div className="hazard-grid">
                  {Object.entries(dossier.climate_risk).map(([hz, r]) => {
                    const pct = Math.round(r.value * (r.value <= 1 ? 100 : 1));
                    return (
                      <div key={hz} className="hazard-card">
                        <div className="hazard-top">
                          <span className="hazard-name">{hz}</span>
                          <span className="hazard-val" style={{ color: riskColor(pct) }}>
                            {pct} · {r.label}
                          </span>
                        </div>
                        <div className="hazard-track">
                          <div
                            className="hazard-fill"
                            style={{ width: `${pct}%`, background: riskColor(pct) }}
                          />
                        </div>
                        <div className="muted">{HAZARD_DESC[hz] ?? "Ameaça climática"}</div>
                      </div>
                    );
                  })}
                </div>
              </>
            ) : (
              <div className="muted">
                Sem índice municipal no AdaptaBrasil para esta localização (ou localização não
                resolvida).
              </div>
            )}
          </section>

          <CompanyAnalytics dossier={dossier} />

          <Relationships dossier={dossier} />

          {dossier.company_sk != null ? (
            <section className="sub-panel analysis">
              <div className="analysis-head">
                <h4>Análise da plataforma — scores e ML</h4>
                {scenarios.length > 0 && (
                  <div className="mini-controls">
                    <select value={scenario} onChange={(e) => setScenario(e.target.value)}>
                      {scenarios.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
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
                )}
              </div>

              <div className="cards">
                <ScoreCard label="Risco físico" band={entry?.physical ?? null} />
                <ScoreCard label="Risco de transição" band={entry?.transition ?? null} />
                <ScoreCard label="Score composto" band={entry?.composite ?? null} />
              </div>

              {entry?.transition_detail && (
                <div className="report-grid two">
                  <div>
                    <h4>Decomposição do risco de transição</h4>
                    <SubScores detail={entry.transition_detail} />
                  </div>
                  <div>
                    <h4>Impacto financeiro projetado (DCF · NGFS)</h4>
                    {finEntry ? (
                      <div className="fin-grid">
                        <span className="fin-value">{finEntry.dcf_adjustment_pct.toFixed(1)}%</span>
                        <span className="muted">
                          ajuste no valor projetado · faixa {finEntry.band_low_pct.toFixed(1)}% a{" "}
                          {finEntry.band_high_pct.toFixed(1)}%
                        </span>
                      </div>
                    ) : (
                      <div className="muted">Sem projeção financeira neste cenário.</div>
                    )}
                  </div>
                </div>
              )}

              {narrative && (
                <div className="result-block">
                  <h4>Explicação do score</h4>
                  <Narrative markdown={narrative} />
                </div>
              )}

              <div className="report-grid two">
                <div>
                  <h4>Pares por similaridade (ML)</h4>
                  {peers.length > 0 ? (
                    <div className="peer-list">
                      {peers.map((p) => (
                        <span key={p.company_sk} className="pill">
                          {p.name.replace(/ S\.?A\.?$/, "")}
                          <small> · {p.distance.toFixed(2)}</small>
                        </span>
                      ))}
                    </div>
                  ) : (
                    <div className="muted">Sem pares (features insuficientes).</div>
                  )}
                  <div className="muted" style={{ marginTop: 8 }}>
                    Vizinhos mais próximos por porte, setor e fundamentos (NearestNeighbors).
                  </div>
                </div>
                <div>
                  <h4>Detecção de anomalia (ML)</h4>
                  {anomaly ? (
                    <>
                      <div className="fin-grid">
                        <span
                          className="fin-value"
                          style={{ color: anomaly.is_outlier ? "#ef4444" : "#22c55e" }}
                        >
                          {anomaly.is_outlier ? "Atípica" : "Típica"}
                        </span>
                        <span className="muted">score {anomaly.score.toFixed(3)}</span>
                      </div>
                      <div className="muted" style={{ marginTop: 8 }}>
                        IsolationForest sobre os fundamentos da carteira — sinaliza perfis fora do
                        padrão.
                      </div>
                    </>
                  ) : (
                    <div className="muted">Sem avaliação de anomalia.</div>
                  )}
                </div>
              </div>

              {entry && (entry.physical_run || entry.transition_run) && (
                <div className="audit">
                  {entry.physical_run && (
                    <span>
                      Físico: <code>run #{entry.physical_run.run_sk}</code> · v
                      {entry.physical_run.model_version}
                    </span>
                  )}
                  {entry.transition_run && (
                    <span>
                      Transição: <code>run #{entry.transition_run.run_sk}</code> · v
                      {entry.transition_run.model_version}
                    </span>
                  )}
                </div>
              )}
            </section>
          ) : (
            <section className="sub-panel">
              <h4>Análise preditiva (scores e ML)</h4>
              <div className="muted">
                Esta empresa não está na base interna da plataforma. Scores físico/transição,
                similaridade e detecção de anomalia (ML) estão disponíveis para empresas listadas
                na B3 e para os pilotos. Busque por um <b>ticker</b> (ex.: SHUL4, ITSA4, VALE3) ou
                por <b>Döhler</b>/<b>Schulz</b>.
              </div>
            </section>
          )}

          {dossier.news.length > 0 && (
            <section className="sub-panel">
              <h4>Notícias e exposição na mídia · GDELT ({dossier.news.length})</h4>
              <div className="muted" style={{ marginBottom: 8 }}>
                Controvérsia {Math.round(dossier.controversy_ratio * 100)}% — proporção de matérias
                recentes com tom adverso.
              </div>
              <ul className="news-list">
                {dossier.news.slice(0, 8).map((n, i) => (
                  <li key={i}>
                    <a href={n.url} target="_blank" rel="noreferrer">
                      {n.title || n.domain}
                    </a>
                    <span className="muted"> · {n.domain}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {dossier.errors.length > 0 && (
            <div className="muted">
              Fontes indisponíveis: {dossier.errors.map(friendlyError).join(" · ")}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function Kpi({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="kpi">
      <span className="kpi-label">{label}</span>
      <b className="kpi-value" style={color ? { color } : undefined}>
        {value}
      </b>
    </div>
  );
}

function Kv({ k, v }: { k: string; v: string }) {
  return (
    <div className="kv-row">
      <dt>{k}</dt>
      <dd>{v}</dd>
    </div>
  );
}
