"use client";

/**
 * Progress reports stacked bar chart — shows distribution of pending,
 * observed, and approved progress reports.
 */

import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from "recharts";

interface ProgressReportsData {
  pending: number;
  observed: number;
  approved: number;
}

interface ProgressReportsChartProps {
  data: ProgressReportsData;
}

export function ProgressReportsChart({ data }: ProgressReportsChartProps) {
  const chartData = [
    {
      name: "Informes",
      Pendientes: data.pending,
      Observados: data.observed,
      Aprobados: data.approved,
    },
  ];

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData} aria-label="Estado de informes de avance">
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip formatter={(value: unknown) => [value, "Informes"]} />
        <Legend />
        <Bar dataKey="Pendientes" stackId="reports" fill="#f59e0b" />
        <Bar dataKey="Observados" stackId="reports" fill="#8b5cf6" />
        <Bar dataKey="Aprobados" stackId="reports" fill="#10b981" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
