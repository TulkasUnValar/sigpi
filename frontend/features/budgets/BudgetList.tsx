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
import { useTranslations } from "next-intl";
import { useBudgets } from "@/features/budgets/queries";
import { useBudgetPermissions } from "@/features/budgets/permissions";
import { BUDGET_STATUS_VALUES, formatCurrency } from "@/features/budgets/constants";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { EmptyState } from "@/components/shared/EmptyState";
import { Skeleton } from "@/components/shared/Skeleton";
import type { BudgetFilter, BudgetListItem, BudgetStatus } from "@/features/budgets/types";

export function BudgetList() {
  const [filters, setFilters] = useState<BudgetFilter>({});
  const { data, isLoading, error } = useBudgets(filters);
  const { canManage } = useBudgetPermissions();
  const t = useTranslations("budgets");

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
        {t("list.errorLoading", { message: (error as Error).message })}
      </div>
    );
  }

  const budgets = data?.results ?? [];

  return (
    <div className="space-y-6">
      {/* Header with create CTA */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("list.title")}</h1>
        {canManage && (
          <Link
            href="/budgets/new"
            className="rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90"
          >
            {t("list.createNew")}
          </Link>
        )}
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <select
          value={filters.status ?? ""}
          onChange={(e) =>
            setFilters({ ...filters, status: (e.target.value as BudgetStatus) || undefined })
          }
          className="rounded-md border border-input bg-background px-3 py-2"
        >
          <option value="">{t("list.allStatuses")}</option>
          {BUDGET_STATUS_VALUES.map((status) => (
            <option key={status} value={status}>
              {t(`status.${status}`)}
            </option>
          ))}
        </select>
      </div>

      {/* Table or Empty State */}
      {budgets.length === 0 ? (
        <EmptyState
          title={t("list.emptyTitle")}
          description={t("list.emptyDescription")}
        />
      ) : (
        <div className="rounded-lg border">
          <table className="w-full">
            <thead className="border-b bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left font-medium">{t("table.project")}</th>
                <th className="px-4 py-3 text-left font-medium">{t("table.name")}</th>
                <th className="px-4 py-3 text-right font-medium">{t("table.approvedAmount")}</th>
                <th className="px-4 py-3 text-left font-medium">{t("table.status")}</th>
                <th className="px-4 py-3 text-left font-medium">{t("table.created")}</th>
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
      <td className="px-4 py-3 text-right font-mono">{formatCurrency(budget.approved_amount)}</td>
      <td className="px-4 py-3">
        <StatusBadge status={budget.status} />
      </td>
      <td className="px-4 py-3 text-sm text-muted-foreground">
        {new Date(budget.created_at).toLocaleDateString("es-CO")}
      </td>
    </tr>
  );
}
