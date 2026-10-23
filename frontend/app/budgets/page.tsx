/**
 * Budgets list page — /budgets
 *
 * Thin route wrapper that renders the BudgetList feature component.
 * Follows the same pattern as calls, researchers, products.
 */

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { BudgetList } from "@/features/budgets";

export default function BudgetsPage() {
  return (
    <AuthenticatedLayout>
      <BudgetList />
    </AuthenticatedLayout>
  );
}
