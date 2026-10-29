/**
 * New budget page — /budgets/new
 *
 * Thin route wrapper that renders the BudgetForm feature component in create mode.
 */

"use client";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { BudgetForm } from "@/features/budgets";
import { useTranslations } from "next-intl";

export default function NewBudgetPage() {
  const t = useTranslations("budgets");

  return (
    <AuthenticatedLayout>
      <div className="mx-auto max-w-2xl space-y-6">
        <div>
          <h1 className="text-3xl font-bold">{t("pages.new.title")}</h1>
          <p className="mt-2 text-muted-foreground">
            {t("pages.new.description")}
          </p>
        </div>
        <BudgetForm mode="create" />
      </div>
    </AuthenticatedLayout>
  );
}
