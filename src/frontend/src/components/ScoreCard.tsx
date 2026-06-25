import type { Band } from "../api";
import { severityColor, severityLabel } from "./util";

const clamp = (x: number): number => Math.max(0, Math.min(100, x));

function BandBar({ low, central, high }: { low: number; central: number; high: number }) {
  return (
    <div className="bandbar">
      <div
        className="range-fill"
        style={{ left: `${clamp(low)}%`, width: `${clamp(high) - clamp(low)}%` }}
      />
      <div className="marker" style={{ left: `calc(${clamp(central)}% - 1px)` }} />
    </div>
  );
}

export function ScoreCard({ label, band }: { label: string; band: Band | null }) {
  if (!band) {
    return (
      <div className="score-card">
        <div className="label">{label}</div>
        <div className="muted" style={{ marginTop: 14 }}>
          sem dados neste cenário
        </div>
      </div>
    );
  }
  const color = severityColor(band.central);
  return (
    <div className="score-card">
      <div className="label">{label}</div>
      <div className="value" style={{ color }}>
        {band.central.toFixed(1)}
      </div>
      <div className="range">
        risco {severityLabel(band.central).toLowerCase()} · faixa {band.low.toFixed(1)} –{" "}
        {band.high.toFixed(1)}
      </div>
      <BandBar low={band.low} central={band.central} high={band.high} />
    </div>
  );
}
