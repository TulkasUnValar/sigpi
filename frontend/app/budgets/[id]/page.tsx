/**
 * Budget detail page — /budgets/[id]
 *
 * Thin route wrapper that renders the BudgetDetail feature component.
 */

"use client";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { BudgetDetail } from "@/features/budgets";
import { useParams } from "next/navigation";

export default function BudgetDetailPage() {
  const params = useParams();
  const budgetId = String(params.id);

  return (
    <AuthenticatedLayout>
      <BudgetDetail budgetId={budgetId} />
    </AuthenticatedLayout>
  );
}
