/**
 * New budget page — /budgets/new
 *
 * Thin route wrapper that renders the BudgetForm feature component in create mode.
 */

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { BudgetForm } from "@/features/budgets";

export default function NewBudgetPage() {
  return (
    <AuthenticatedLayout>
      <div className="mx-auto max-w-2xl space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Nuevo presupuesto</h1>
          <p className="mt-2 text-muted-foreground">
            Crea un presupuesto para un proyecto. Solo se permite un presupuesto por proyecto.
          </p>
        </div>
        <BudgetForm mode="create" />
      </div>
    </AuthenticatedLayout>
  );
}
