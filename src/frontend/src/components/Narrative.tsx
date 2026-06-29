import type { ReactNode } from "react";

function formatLine(line: string): ReactNode[] {
  return line.split(/\*\*(.+?)\*\*/g).map((part, i) =>
    i % 2 === 1 ? <strong key={i}>{part}</strong> : <span key={i}>{part}</span>,
  );
}

export function Narrative({ markdown }: { markdown: string | null }) {
  if (!markdown) {
    return <div className="muted">Sem narrativa neste cenário.</div>;
  }
  return (
    <div className="narrative">
      {markdown.split("\n").map((line, i) => (
        <div key={i} className={line.startsWith("- ") ? "narrative-li" : "narrative-p"}>
          {formatLine(line.replace(/^- /, "• "))}
        </div>
      ))}
    </div>
  );
}
