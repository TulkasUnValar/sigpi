/**
 * BudgetExecutionsManager component — Create for budget executions.
 *
 * Spec (PR3):
 *   - Table with columns: Monto, Fecha Ejecución, Autorizado Por, Fecha Autorización.
 *   - Inline form for create (amount + executed_at inputs).
 *   - Show executed sum vs approved amount.
 *   - Role-gated: only canManage can see create.
 *   - RN-020: handle 400 error with authorization dialog.
 *   - Toast success/error.
 *   - EmptyState if no executions.
 *   - Skeleton while loading.
 */

"use client";

import { useState } from "react";
import { useBudgetExecutions } from "@/features/budgets/queries";
import { useCreateBudgetExecution } from "@/features/budgets/mutations";
import { useBudgetPermissions } from "@/features/budgets/permissions";
import { formatCurrency, parseDecimal } from "@/features/budgets/constants";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { toast } from "sonner";
import { useAuthStore } from "@/store/auth";
import type { BudgetExecution } from "@/features/budgets/types";

interface BudgetExecutionsManagerProps {
  budgetId: string;
  lineId: string;
  lineApprovedAmount: string;
}

export function BudgetExecutionsManager({
  budgetId,
  lineId,
  lineApprovedAmount,
}: BudgetExecutionsManagerProps) {
  const { data: executions, isLoading, error } = useBudgetExecutions(budgetId, lineId);
  const createMutation = useCreateBudgetExecution(budgetId, lineId);
  const { canManage, canAuthorize } = useBudgetPermissions();
  const user = useAuthStore((state) => state.user);

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [authorizationDialog, setAuthorizationDialog] = useState<{
    amount: string;
    executed_at: string;
  } | null>(null);

  // Form state
  const [formAmount, setFormAmount] = useState("");
  const [formExecutedAt, setFormExecutedAt] = useState("");

  if (isLoading) {
    return <Skeleton className="h-64 w-full" />;
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-destructive">
        Error al cargar ejecuciones: {(error as Error).message}
      </div>
    );
  }

  const executionsArray = executions ?? [];
  const totalExecuted = executionsArray.reduce(
    (sum, exec) => sum + parseDecimal(exec.amount),
    0
  );
  const approvedAmount = parseDecimal(lineApprovedAmount);

  const handleCreate = async () => {
    if (!formAmount.trim() || !formExecutedAt.trim()) {
      toast.error("Complete todos los campos.");
      return;
    }

    const amountNum = parseDecimal(formAmount);
    const currentTotal = totalExecuted;
    const newTotal = currentTotal + amountNum;

    // Check if this execution would exceed the approved amount
    if (newTotal > approvedAmount) {
      // Show authorization dialog
      setAuthorizationDialog({
        amount: formAmount.trim(),
        executed_at: formExecutedAt.trim(),
      });
      return;
    }

    try {
      await createMutation.mutateAsync({
        amount: formAmount.trim(),
        executed_at: formExecutedAt.trim(),
      });
      setFormAmount("");
      setFormExecutedAt("");
      setShowCreateForm(false);
    } catch (error) {
      // Error already handled by mutation onError
      console.error("Error creating execution:", error);
    }
  };

  const handleAuthorizedCreate = async () => {
    if (!authorizationDialog) return;

    if (!canAuthorize) {
      toast.error("No tiene permisos para autorizar sobre-ejecuciones.");
      setAuthorizationDialog(null);
      return;
    }

    try {
      await createMutation.mutateAsync({
        amount: authorizationDialog.amount,
        executed_at: authorizationDialog.executed_at,
        authorized_by: user?.id ?? null,
        authorized_at: new Date().toISOString().split("T")[0],
      });
      setFormAmount("");
      setFormExecutedAt("");
      setShowCreateForm(false);
      setAuthorizationDialog(null);
    } catch (error) {
      // Error already handled by mutation onError
      console.error("Error creating authorized execution:", error);
    }
  };

  const startCreate = () => {
    setShowCreateForm(true);
    setFormAmount("");
    setFormExecutedAt("");
  };

  const cancelCreate = () => {
    setShowCreateForm(false);
    setFormAmount("");
    setFormExecutedAt("");
  };

  const isFormPending = createMutation.isPending;

  return (
    <div className="space-y-4">
      {/* Header with create CTA */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Ejecuciones del Rubro</h2>
        {canManage && !showCreateForm && (
          <button
            onClick={startCreate}
            className="rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90"
          >
            Registrar ejecución
          </button>
        )}
      </div>

      {/* Create Form */}
      {showCreateForm && (
        <div className="rounded-lg border bg-card p-4 space-y-3">
          <div>
            <label className="block text-sm font-medium mb-1">Monto</label>
            <input
              type="text"
              value={formAmount}
              onChange={(e) => setFormAmount(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2"
              placeholder="0.00"
              aria-label="Monto de la ejecución"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">
              Fecha de Ejecución
            </label>
            <input
              type="date"
              value={formExecutedAt}
              onChange={(e) => setFormExecutedAt(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2"
              aria-label="Fecha de ejecución"
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleCreate}
              disabled={isFormPending}
              className="rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              Registrar
            </button>
            <button
              onClick={cancelCreate}
              className="rounded-md border border-input px-4 py-2 hover:bg-muted"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {/* Table or Empty State */}
      {executionsArray.length === 0 ? (
        <EmptyState
          title="No hay ejecuciones"
          description="Aún no se han registrado ejecuciones para este rubro."
        />
      ) : (
        <div className="rounded-lg border">
          <table className="w-full">
            <thead className="border-b bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-right font-medium">Monto</th>
                <th className="px-4 py-3 text-left font-medium">
                  Fecha Ejecución
                </th>
                <th className="px-4 py-3 text-left font-medium">
                  Autorizado Por
                </th>
                <th className="px-4 py-3 text-left font-medium">
                  Fecha Autorización
                </th>
              </tr>
            </thead>
            <tbody>
              {executionsArray.map((execution: BudgetExecution) => (
                <tr
                  key={execution.id}
                  className="border-b transition-colors hover:bg-muted/50"
                >
                  <td className="px-4 py-3 text-right font-mono">
                    {formatCurrency(execution.amount)}
                  </td>
                  <td className="px-4 py-3">
                    {new Date(execution.executed_at).toLocaleDateString("es-CO")}
                  </td>
                  <td className="px-4 py-3">
                    {execution.authorized_by || "—"}
                  </td>
                  <td className="px-4 py-3">
                    {execution.authorized_at
                      ? new Date(execution.authorized_at).toLocaleDateString("es-CO")
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Summary */}
      <div className="text-sm text-muted-foreground">
        Ejecutado: {formatCurrency(totalExecuted)} de {formatCurrency(approvedAmount)} aprobado
      </div>

      {/* Authorization Dialog */}
      <ConfirmDialog
        open={!!authorizationDialog}
        onOpenChange={(open) => !open && setAuthorizationDialog(null)}
        title="Sobre-ejecución detectada"
        description="La ejecución excede el presupuesto aprobado del rubro. ¿Desea autorizar esta ejecución?"
        confirmLabel="Autorizar"
        cancelLabel="Cancelar"
        destructive={false}
        onConfirm={handleAuthorizedCreate}
      />
    </div>
  );
}
