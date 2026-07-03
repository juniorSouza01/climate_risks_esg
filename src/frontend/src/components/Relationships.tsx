import type { Dossier } from "../api";
import { Seal } from "./CompanyAnalytics";

export function Relationships({ dossier }: { dossier: Dossier }) {
  const r = dossier.relationships;
  if (!r) {
    return (
      <section className="sub-panel">
        <h4>Relacionamentos & cadeia de valor</h4>
        <div className="muted">
          Disponível apenas na busca por CNPJ — é o CNPJ que resolve os relacionamentos públicos.
        </div>
      </section>
    );
  }

  const gs = r.gov_supplier;
  const soc = r.socios;
  const vc = r.value_chain;
  const pc = r.public_contracts;

  return (
    <section className="sub-panel">
      <h4>Relacionamentos & cadeia de valor</h4>
      <p className="muted" style={{ marginTop: -4 }}>
        Face pública e factual da cadeia (não há base aberta de relações B2B privadas no Brasil).
      </p>

      <div className="report-grid">
        <div className="pred-card">
          <div className="cross-top">
            <span>Fornecedor do governo federal</span>
            <Seal kind="factual" />
          </div>
          {gs == null ? (
            <div className="muted">não consultado</div>
          ) : gs.found === false ? (
            <div className="muted">Não consta como fornecedor federal (Compras.gov).</div>
          ) : (
            <>
              <div
                className="cross-val"
                style={{ fontSize: 18, color: gs.habilitado_licitar ? "#22c55e" : "#8a98b5" }}
              >
                {gs.habilitado_licitar ? "Habilitado a licitar" : "Cadastrado (não habilitado)"}
              </div>
              <div className="muted">
                {[gs.porte, gs.municipio && `${gs.municipio}/${gs.uf ?? ""}`]
                  .filter(Boolean)
                  .join(" · ")}
              </div>
              {gs.note && (
                <div className="muted" style={{ marginTop: 4 }}>
                  {gs.note}
                </div>
              )}
            </>
          )}
        </div>

        <div className="pred-card">
          <div className="cross-top">
            <span>Quadro societário (QSA)</span>
            <Seal kind="factual" />
          </div>
          {soc && soc.count > 0 ? (
            <div className="muted">{soc.items.join(" · ")}</div>
          ) : (
            <div className="muted">não consta</div>
          )}
        </div>
      </div>

      {vc && (
        <div className="result-block">
          <div className="cross-top" style={{ marginBottom: 8 }}>
            <span>
              Cadeia de valor estimada — {vc.archetype}
              {vc.assumed ? " (setor assumido pelo cadastro)" : ""}
            </span>
            <Seal kind="inferido" />
          </div>
          <div className="chain-row">
            <span className="chain-tag">Fornecedores (montante)</span>
            {(vc.upstream ?? []).map((u, i) => (
              <span key={i} className="chain-chip">
                {u.label}
              </span>
            ))}
          </div>
          <div className="chain-row">
            <span className="chain-tag">Clientes (jusante)</span>
            {(vc.downstream ?? []).map((u, i) => (
              <span key={i} className="chain-chip">
                {u.label}
              </span>
            ))}
          </div>
          {vc.methodology && (
            <div className="muted" style={{ marginTop: 6 }}>
              {vc.methodology}
            </div>
          )}
        </div>
      )}

      {pc && (
        <div className="result-block">
          <div className="cross-top">
            <span>Contratos públicos com valores (clientes factuais)</span>
            <Seal kind="previsto" />
          </div>
          <div className="muted">
            {pc.available
              ? "disponível — Portal da Transparência"
              : `Requer token do Portal da Transparência para listar órgãos-cliente e valores (${pc.reason ?? ""}).`}
          </div>
        </div>
      )}
    </section>
  );
}
