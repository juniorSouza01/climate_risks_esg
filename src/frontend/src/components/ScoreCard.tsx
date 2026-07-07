import type { Availability, Band } from "../api";
import { severityColor, severityLabel } from "./util";

const clamp = (x: number): number => Math.max(0, Math.min(100, x));

const fmt1 = (v: number | null | undefined): string =>
  v == null || !Number.isFinite(v) ? "—" : v.toFixed(1);

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

export function ScoreCard({
  label,
  band,
  availability,
  reason,
}: {
  label: string;
  band: Band | null;
  availability?: Availability;
  reason?: string | null;
}) {
  if (
    !band ||
    (band.availability != null && band.availability !== "available") ||
    band.central == null
  ) {
    const entryReason =
      availability != null && availability !== "available" ? reason : null;
    return (
      <div className="score-card">
        <div className="label">{label}</div>
        <div className="muted" style={{ marginTop: 14 }}>
          {band?.reason || entryReason || "sem dados neste cenário"}
        </div>
      </div>
    );
  }
  const color = severityColor(band.central);
  return (
    <div className="score-card">
      <div className="label">{label}</div>
      <div className="value" style={{ color }}>
        {fmt1(band.central)}
      </div>
      <div className="range">
        risco {severityLabel(band.central).toLowerCase()} · faixa {fmt1(band.low)} –{" "}
        {fmt1(band.high)}
      </div>
      <BandBar
        low={band.low ?? band.central}
        central={band.central}
        high={band.high ?? band.central}
      />
    </div>
  );
}
