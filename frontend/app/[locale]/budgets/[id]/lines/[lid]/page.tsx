/**
 * Budget Line Detail page — displays details of a single budget line.
 *
 * Spec (PR2):
 *   - Thin wrapper that renders BudgetLineDetail component.
 *   - Shows: nombre, approved_amount, created_at, updated_at.
 *   - "Volver a presupuesto" link that navigates to /budgets/[id].
 */

"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useBudgetLines } from "@/features/budgets/queries";
import { formatCurrency } from "@/features/budgets/constants";
import { Skeleton } from "@/components/shared/Skeleton";
import { useTranslations } from "next-intl";

export default function BudgetLineDetailPage() {
  const params = useParams<{ id: string; lid: string }>();
  const budgetId = params.id;
  const lineId = params.lid;
  const t = useTranslations("budgets");

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
        {t("pages.lineDetail.errorLoading", { message: (error as Error).message })}
      </div>
    );
  }

  const line = lines?.find((l) => l.id === lineId);

  if (!line) {
    return (
      <div className="rounded-lg border p-4">
        <p className="text-muted-foreground">{t("pages.lineDetail.notFound")}</p>
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
          {t("pages.lineDetail.backToBudget")}
        </Link>
        <h1 className="text-3xl font-bold">{line.name}</h1>
      </div>

      <div className="rounded-lg border bg-card p-6">
        <h2 className="mb-4 text-xl font-semibold">{t("pages.lineDetail.detailsTitle")}</h2>
        <dl className="grid grid-cols-2 gap-4">
          <div>
            <dt className="text-sm font-medium text-muted-foreground">
              {t("table.approvedAmount")}
            </dt>
            <dd className="mt-1 text-lg font-mono">
              {formatCurrency(line.approved_amount)}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-muted-foreground">{t("table.created")}</dt>
            <dd className="mt-1 text-sm">
              {new Date(line.created_at).toLocaleString("es-CO")}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-muted-foreground">
              {t("table.updated")}
            </dt>
            <dd className="mt-1 text-sm">
              {new Date(line.updated_at).toLocaleString("es-CO")}
            </dd>
          </div>
        </dl>
      </div>
    </div>
  );
}
