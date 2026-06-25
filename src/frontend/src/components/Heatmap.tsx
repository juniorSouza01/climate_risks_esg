import type { Company, CompanyScores } from "../api";
import { severityColor } from "./util";

interface Props {
  companies: Company[];
  scoresById: Record<number, CompanyScores>;
  scenario: string;
  horizons: number[];
  selectedId: number | null;
  onSelect: (id: number) => void;
}

export function Heatmap({ companies, scoresById, scenario, horizons, selectedId, onSelect }: Props) {
  return (
    <div className="heatmap">
      <div className="heatmap-row heatmap-head">
        <div className="heatmap-name muted">Empresa \ Horizonte</div>
        {horizons.map((h) => (
          <div key={h} className="heatmap-cell head">
            {h}
          </div>
        ))}
      </div>
      {companies.map((c) => {
        const sc = scoresById[c.company_sk];
        return (
          <div
            key={c.company_sk}
            className={"heatmap-row clickable" + (c.company_sk === selectedId ? " active" : "")}
            onClick={() => onSelect(c.company_sk)}
          >
            <div className="heatmap-name">{c.name.replace(/ S\.A\.?$/, "")}</div>
            {horizons.map((h) => {
              const e = sc?.scores.find(
                (s) => s.scenario === scenario && s.horizon_year === h,
              );
              const v = e?.composite?.central ?? null;
              return (
                <div
                  key={h}
                  className="heatmap-cell"
                  style={{ background: v == null ? "#1a2233" : severityColor(v) }}
                  title={v == null ? "sem dados" : v.toFixed(1)}
                >
                  {v == null ? "—" : v.toFixed(0)}
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}
