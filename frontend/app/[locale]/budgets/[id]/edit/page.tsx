/**
 * Edit budget page — /budgets/[id]/edit
 *
 * Thin route wrapper that renders the BudgetForm feature component in edit mode.
 */

"use client";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { BudgetForm, useBudget } from "@/features/budgets";
import { useParams } from "next/navigation";
import { Skeleton } from "@/components/shared/Skeleton";
import { useTranslations } from "next-intl";

export default function EditBudgetPage() {
  const params = useParams();
  const budgetId = String(params.id);
  const { data: budget, isLoading, error } = useBudget(budgetId);
  const t = useTranslations("budgets");

  if (isLoading) {
    return (
      <AuthenticatedLayout>
        <div className="mx-auto max-w-2xl space-y-4">
          <Skeleton className="h-8 w-1/3" />
          <Skeleton className="h-64 w-full" />
        </div>
      </AuthenticatedLayout>
    );
  }

  if (error) {
    return (
      <AuthenticatedLayout>
        <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-destructive">
          {t("pages.edit.errorLoading", { message: (error as Error).message })}
        </div>
      </AuthenticatedLayout>
    );
  }

  if (!budget) {
    return (
      <AuthenticatedLayout>
        <div className="rounded-lg border p-4">
          <p className="text-muted-foreground">{t("pages.edit.notFound")}</p>
        </div>
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <div className="mx-auto max-w-2xl space-y-6">
        <div>
          <h1 className="text-3xl font-bold">{t("pages.edit.title")}</h1>
          <p className="mt-2 text-muted-foreground">
            {t("pages.edit.description")}
          </p>
        </div>
        <BudgetForm mode="edit" budget={budget} />
      </div>
    </AuthenticatedLayout>
  );
}
