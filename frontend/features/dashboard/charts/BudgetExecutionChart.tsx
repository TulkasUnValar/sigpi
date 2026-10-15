"use client";

/**
 * Budget execution bar chart — compares approved, executed, and remaining
 * budget amounts.
 */

import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from "recharts";

interface BudgetData {
  approved: string;
  executed: string;
  balance: string;
}

interface BudgetExecutionChartProps {
  data: BudgetData;
}

function parseAmount(value: string): number {
  return parseFloat(value) || 0;
}

export function BudgetExecutionChart({ data }: BudgetExecutionChartProps) {
  const chartData = [
    {
      name: "Presupuesto",
      Aprobado: parseAmount(data.approved),
      Ejecutado: parseAmount(data.executed),
      Saldo: parseAmount(data.balance),
    },
  ];

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData} aria-label="Ejecución presupuestal">
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip
          formatter={(value: unknown) => [
            new Intl.NumberFormat("es-CO", {
              style: "currency",
              currency: "COP",
              minimumFractionDigits: 0,
            }).format(Number(value)),
          ]}
        />
        <Legend />
        <Bar dataKey="Aprobado" fill="#10b981" radius={[4, 4, 0, 0]} />
        <Bar dataKey="Ejecutado" fill="#3b82f6" radius={[4, 4, 0, 0]} />
        <Bar dataKey="Saldo" fill="#f59e0b" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
