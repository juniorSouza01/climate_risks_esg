export function severityColor(score: number): string {
  if (score < 33) return "#22c55e";
  if (score < 66) return "#f59e0b";
  return "#ef4444";
}

export function severityLabel(score: number): string {
  if (score < 33) return "Baixo";
  if (score < 66) return "Moderado";
  return "Alto";
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
