/**
 * BudgetList component — paginated table of budgets with filters.
 *
 * Spec (budgets-ui):
 *   - Paginated table with project name, approved amount, status.
 *   - Filters: project, status.
 *   - Empty state when no budgets.
 *   - Role-gated create CTA (admin/director only).
 *   - Summary indicators (approved/executed/balance) per row.
 */

"use client";

import Link from "next/link";
import { useState } from "react";
import { useBudgets } from "@/features/budgets/queries";
import { useBudgetPermissions } from "@/features/budgets/permissions";
import { BUDGET_STATUS_LABELS, BUDGET_STATUS_OPTIONS, formatCurrency } from "@/features/budgets/constants";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { EmptyState } from "@/components/shared/EmptyState";
import { Skeleton } from "@/components/shared/Skeleton";
import type { BudgetFilter, BudgetListItem, BudgetStatus } from "@/features/budgets/types";

export function BudgetList() {
  const [filters, setFilters] = useState<BudgetFilter>({});
  const { data, isLoading, error } = useBudgets(filters);
  const { canManage } = useBudgetPermissions();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-destructive">
        Error al cargar presupuestos: {(error as Error).message}
      </div>
    );
  }

  const budgets = data?.results ?? [];

  return (
    <div className="space-y-6">
      {/* Header with create CTA */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Presupuestos</h1>
        {canManage && (
          <Link
            href="/budgets/new"
            className="rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90"
          >
            Nuevo presupuesto
          </Link>
        )}
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <select
          value={filters.status ?? ""}
          onChange={(e) => setFilters({ ...filters, status: e.target.value || undefined })}
          className="rounded-md border border-input bg-background px-3 py-2"
        >
          <option value="">Todos los estados</option>
          {BUDGET_STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Table or Empty State */}
      {budgets.length === 0 ? (
        <EmptyState
          title="No hay presupuestos"
          description="Aún no se han creado presupuestos para los proyectos."
        />
      ) : (
        <div className="rounded-lg border">
          <table className="w-full">
            <thead className="border-b bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Proyecto</th>
                <th className="px-4 py-3 text-left font-medium">Nombre</th>
                <th className="px-4 py-3 text-right font-medium">Monto Aprobado</th>
                <th className="px-4 py-3 text-left font-medium">Estado</th>
                <th className="px-4 py-3 text-left font-medium">Creado</th>
              </tr>
            </thead>
            <tbody>
              {budgets.map((budget) => (
                <BudgetRow key={budget.id} budget={budget} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function BudgetRow({ budget }: { budget: BudgetListItem }) {
  return (
    <tr className="border-b transition-colors hover:bg-muted/50">
      <td className="px-4 py-3">
        <Link href={`/budgets/${budget.id}`} className="font-medium text-primary hover:underline">
          {budget.project_name}
        </Link>
      </td>
      <td className="px-4 py-3">{budget.name}</td>
      <td className="px-4 py-3 text-right font-mono">
        {formatCurrency(budget.approved_amount)}
      </td>
      <td className="px-4 py-3">
        <StatusBadge status={budget.status} label={BUDGET_STATUS_LABELS[budget.status as BudgetStatus]} />
      </td>
      <td className="px-4 py-3 text-sm text-muted-foreground">
        {new Date(budget.created_at).toLocaleDateString("es-CO")}
      </td>
    </tr>
  );
}
