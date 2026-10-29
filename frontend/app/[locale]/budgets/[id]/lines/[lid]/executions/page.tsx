/**
 * Budget Executions page — /budgets/[id]/lines/[lid]/executions
 *
 * Thin route wrapper that renders BudgetExecutionsManager.
 */

"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useBudgetLines } from "@/features/budgets/queries";
import { BudgetExecutionsManager } from "@/features/budgets/BudgetExecutionsManager";
import { Skeleton } from "@/components/shared/Skeleton";

export default function BudgetExecutionsPage() {
  const params = useParams<{ id: string; lid: string }>();
  const budgetId = params.id;
  const lineId = params.lid;

  const { data: lines, isLoading, error } = useBudgetLines(budgetId);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-destructive">
        Error al cargar línea: {(error as Error).message}
      </div>
    );
  }

  const line = lines?.find((l) => l.id === lineId);

  if (!line) {
    return (
      <div className="rounded-lg border p-4">
        <p className="text-muted-foreground">Línea no encontrada.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <Link
          href={`/budgets/${budgetId}`}
          className="mb-2 inline-block text-sm text-muted-foreground hover:text-foreground"
        >
          ← Volver a líneas
        </Link>
        <h1 className="text-3xl font-bold">Ejecuciones — {line.name}</h1>
      </div>

      <BudgetExecutionsManager
        budgetId={budgetId}
        lineId={lineId}
        lineApprovedAmount={line.approved_amount}
      />
    </div>
  );
}
