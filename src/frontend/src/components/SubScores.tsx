import type { TransitionDetail } from "../api";
import { severityColor } from "./util";

const clamp = (x: number): number => Math.max(0, Math.min(100, x));

function Row({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="subscore">
      <div className="subscore-head">
        <span>{label}</span>
        <span>{value == null ? "—" : value.toFixed(0)}</span>
      </div>
      <div className="subscore-track">
        <div
          className="subscore-fill"
          style={{
            width: `${value == null ? 0 : clamp(value)}%`,
            background: severityColor(value ?? 0),
          }}
        />
      </div>
    </div>
  );
}

export function SubScores({ detail }: { detail: TransitionDetail | null }) {
  if (!detail) {
    return <div className="muted">Sem detalhe de transição neste cenário.</div>;
  }
  return (
    <div>
      <Row label="Política" value={detail.policy} />
      <Row label="Tecnológico" value={detail.tech} />
      <Row label="Mercado" value={detail.market} />
      <div className="chips">
        <span className="chip-metric">
          Intensidade de carbono
          <b>{detail.carbon_intensity == null ? "—" : detail.carbon_intensity.toFixed(2)}</b>
        </span>
        <span className="chip-metric">
          Alinhamento de metas
          <b>{detail.target_alignment == null ? "—" : detail.target_alignment.toFixed(2)}</b>
        </span>
      </div>
    </div>
  );
}
