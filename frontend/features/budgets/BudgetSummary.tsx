/**
 * BudgetSummary component — displays IND-007/008/009 indicators.
 *
 * Spec (budgets-ui):
 *   - Shows approved, executed, and balance totals.
 *   - Uses formatCurrency for display.
 *   - Loading and error states.
 */

"use client";

import { useTranslations } from "next-intl";
import { useBudgetSummary } from "@/features/budgets/queries";
import { formatCurrency } from "@/features/budgets/constants";
import { Skeleton } from "@/components/shared/Skeleton";

interface BudgetSummaryProps {
  budgetId: string;
}

export function BudgetSummary({ budgetId }: BudgetSummaryProps) {
  const { data: summary, isLoading, error } = useBudgetSummary(budgetId);
  const t = useTranslations("budgets");

  if (isLoading) {
    return (
      <div className="grid grid-cols-3 gap-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-destructive">
        {t("summary.errorLoading", { message: (error as Error).message })}
      </div>
    );
  }

  if (!summary) {
    return null;
  }

  const approved = parseFloat(summary.approved);
  const executed = parseFloat(summary.executed);
  const balance = parseFloat(summary.balance);
  const executionPercentage = approved > 0 ? (executed / approved) * 100 : 0;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-4">
        {/* IND-007: Approved */}
        <div className="rounded-lg border bg-card p-4">
          <p className="text-sm text-muted-foreground">{t("summary.approved")}</p>
          <p className="mt-2 text-2xl font-bold text-primary">{formatCurrency(summary.approved)}</p>
        </div>

        {/* IND-008: Executed */}
        <div className="rounded-lg border bg-card p-4">
          <p className="text-sm text-muted-foreground">{t("summary.executed")}</p>
          <p className="mt-2 text-2xl font-bold text-accent">{formatCurrency(summary.executed)}</p>
          <div className="mt-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>{executionPercentage.toFixed(1)}%</span>
            </div>
            <div className="mt-1 h-2 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full bg-accent transition-all"
                style={{ width: `${Math.min(executionPercentage, 100)}%` }}
              />
            </div>
          </div>
        </div>

        {/* IND-009: Balance */}
        <div className="rounded-lg border bg-card p-4">
          <p className="text-sm text-muted-foreground">{t("summary.balance")}</p>
          <p
            className={`mt-2 text-2xl font-bold ${
              balance < 0 ? "text-destructive" : "text-success"
            }`}
          >
            {formatCurrency(summary.balance)}
          </p>
        </div>
      </div>
    </div>
  );
}
