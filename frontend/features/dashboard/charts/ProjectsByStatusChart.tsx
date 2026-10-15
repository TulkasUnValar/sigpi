"use client";

/**
 * Projects by status pie chart — visualizes project distribution across
 * different statuses (aprobado, en_ejecucion, suspendido, etc.).
 */

import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";

interface StatusData {
  status: string;
  count: number;
}

interface ProjectsByStatusChartProps {
  data: StatusData[];
}

const STATUS_COLORS: Record<string, string> = {
  aprobado: "#10b981",
  en_ejecucion: "#3b82f6",
  suspendido: "#f59e0b",
  en_revision: "#8b5cf6",
  cerrado: "#6b7280",
};

function getColor(status: string): string {
  return STATUS_COLORS[status] ?? "#94a3b8";
}

export function ProjectsByStatusChart({ data }: ProjectsByStatusChartProps) {
  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-muted-foreground">
        No hay datos de proyectos por estado
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart aria-label="Distribución de proyectos por estado">
        <Pie
          data={data}
          dataKey="count"
          nameKey="status"
          cx="50%"
          cy="50%"
          outerRadius={80}
          label={(entry: StatusData) => `${entry.status}: ${entry.count}`}
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={getColor(entry.status)} />
          ))}
        </Pie>
        <Tooltip formatter={(value) => [value, "Proyectos"]} />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}
