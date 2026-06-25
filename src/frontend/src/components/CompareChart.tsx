import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface CompareRow {
  name: string;
  fisico: number | null;
  transicao: number | null;
  composto: number | null;
}

export function CompareChart({ data }: { data: CompareRow[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#243049" />
        <XAxis dataKey="name" stroke="#8a98b5" fontSize={12} />
        <YAxis domain={[0, 100]} stroke="#8a98b5" fontSize={12} />
        <Tooltip
          contentStyle={{
            background: "#121a2e",
            border: "1px solid #243049",
            borderRadius: 8,
            color: "#e6edf7",
          }}
          cursor={{ fill: "rgba(255,255,255,0.04)" }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="fisico" name="Físico" fill="#38bdf8" radius={[4, 4, 0, 0]} />
        <Bar dataKey="transicao" name="Transição" fill="#a78bfa" radius={[4, 4, 0, 0]} />
        <Bar dataKey="composto" name="Composto" fill="#f59e0b" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
