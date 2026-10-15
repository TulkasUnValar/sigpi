"use client";

/**
 * Projects by center bar chart — shows project count per research center.
 */

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

interface CenterData {
  center_id: string;
  name: string;
  count: number;
}

interface ProjectsByCenterChartProps {
  data: CenterData[];
}

export function ProjectsByCenterChart({ data }: ProjectsByCenterChartProps) {
  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-muted-foreground">
        No hay datos de proyectos por centro
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} aria-label="Proyectos por centro de investigación">
        <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} />
        <YAxis />
        <Tooltip formatter={(value) => [value, "Proyectos"]} />
        <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
