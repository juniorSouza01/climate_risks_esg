export const SEVERITY_CUTS = [33, 66] as const;

export function severityColor(score: number): string {
  if (score < SEVERITY_CUTS[0]) return "#22c55e";
  if (score < SEVERITY_CUTS[1]) return "#f59e0b";
  return "#ef4444";
}

export function severityLabel(score: number): string {
  if (score < SEVERITY_CUTS[0]) return "Baixo";
  if (score < SEVERITY_CUTS[1]) return "Moderado";
  return "Alto";
}

export function fmtBRL(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return "—";
  if (Math.abs(v) >= 1e9) return "R$ " + (v / 1e9).toFixed(2) + " bi";
  if (Math.abs(v) >= 1e6) return "R$ " + (v / 1e6).toFixed(2) + " mi";
  if (Math.abs(v) >= 1e3) return "R$ " + (v / 1e3).toFixed(0) + " mil";
  return "R$ " + v.toFixed(0);
}

export function avg(xs: number[]): number {
  return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0;
}

export function fmtDate(iso: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? "—"
    : d.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}
