/**
 * BudgetLinesManager component — CRUD for budget lines (rubros).
 *
 * Spec (PR2):
 *   - Table with columns: Nombre, Monto Aprobado, Acciones (edit/delete).
 *   - Inline form for create/edit (name + approved_amount inputs).
 *   - Sum validation: warn if sum > budgetApprovedAmount.
 *   - Role-gated: only canManage can see create/edit/delete.
 *   - ConfirmDialog for delete.
 *   - Toast success/error.
 *   - EmptyState if no lines.
 *   - Skeleton while loading.
 */

"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useBudgetLines } from "@/features/budgets/queries";
import {
  useCreateBudgetLine,
  useUpdateBudgetLine,
  useDeleteBudgetLine,
} from "@/features/budgets/mutations";
import { useBudgetPermissions } from "@/features/budgets/permissions";
import { formatCurrency, parseDecimal } from "@/features/budgets/constants";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { toast } from "sonner";
import type { BudgetLine } from "@/features/budgets/types";

interface BudgetLinesManagerProps {
  budgetId: string;
  budgetApprovedAmount: string;
}

export function BudgetLinesManager({
  budgetId,
  budgetApprovedAmount,
}: BudgetLinesManagerProps) {
  const { data: lines, isLoading, error } = useBudgetLines(budgetId);
  const createMutation = useCreateBudgetLine(budgetId);
  const { canManage } = useBudgetPermissions();
  const t = useTranslations("budgets");
  const tc = useTranslations("common");

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingLine, setEditingLine] = useState<BudgetLine | null>(null);
  const [deleteLine, setDeleteLine] = useState<BudgetLine | null>(null);

  // Form state
  const [formName, setFormName] = useState("");
  const [formAmount, setFormAmount] = useState("");

  // Hooks for update/delete — called with current editing/deleting line id.
  // The component re-renders when editingLine/deleteLine change, so the hooks
  // are recreated with the new id each time.
  const updateMutation = useUpdateBudgetLine(budgetId, editingLine?.id ?? "");
  const deleteMutation = useDeleteBudgetLine(budgetId);

  const linesArray = useMemo(() => lines ?? [], [lines]);
  const totalLines = useMemo(
    () => linesArray.reduce((sum, line) => sum + parseDecimal(line.approved_amount), 0),
    [linesArray]
  );

  if (isLoading) {
    return <Skeleton className="h-64 w-full" />;
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-destructive">
        {t("lines.errorLoading", { message: (error as Error).message })}
      </div>
    );
  }

  const budgetLimit = parseDecimal(budgetApprovedAmount);
  const exceedsBudget = totalLines > budgetLimit;

  const validateAmount = (value: string): boolean => {
    const num = parseFloat(value);
    return !isNaN(num) && num >= 0;
  };

  const handleCreate = async () => {
    if (!formName.trim() || !formAmount.trim()) {
      toast.error(t("lines.fillAllFields"));
      return;
    }

    if (!validateAmount(formAmount)) {
      toast.error(t("lines.invalidAmount"));
      return;
    }

    try {
      await createMutation.mutateAsync({
        name: formName.trim(),
        approved_amount: formAmount.trim(),
      });
      setFormName("");
      setFormAmount("");
      setShowCreateForm(false);
    } catch (error) {
      // Error already handled by mutation onError
      console.error("Error creating line:", error);
    }
  };

  const handleUpdate = async () => {
    if (!editingLine) return;
    if (!formName.trim() || !formAmount.trim()) {
      toast.error(t("lines.fillAllFields"));
      return;
    }

    try {
      await updateMutation.mutateAsync({
        name: formName.trim(),
        approved_amount: formAmount.trim(),
      });
      setEditingLine(null);
      setFormName("");
      setFormAmount("");
    } catch (error) {
      // Error already handled by mutation onError
      console.error("Error updating line:", error);
    }
  };

  const handleDelete = async () => {
    if (!deleteLine) return;
    try {
      await deleteMutation.mutateAsync(deleteLine.id);
      setDeleteLine(null);
    } catch (error) {
      // Error already handled by mutation onError
      console.error("Error deleting line:", error);
    }
  };

  const startEdit = (line: BudgetLine) => {
    setEditingLine(line);
    setFormName(line.name);
    setFormAmount(line.approved_amount);
    setShowCreateForm(false);
  };

  const cancelEdit = () => {
    setEditingLine(null);
    setFormName("");
    setFormAmount("");
  };

  const startCreate = () => {
    setEditingLine(null);
    setShowCreateForm(true);
    setFormName("");
    setFormAmount("");
  };

  const cancelCreate = () => {
    setShowCreateForm(false);
    setFormName("");
    setFormAmount("");
  };

  const isFormPending = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="space-y-4">
      {/* Header with create CTA */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">{t("lines.title")}</h2>
        {canManage && !showCreateForm && !editingLine && (
          <button
            onClick={startCreate}
            className="rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90"
          >
            {t("lines.addLine")}
          </button>
        )}
      </div>

      {/* Warning if exceeds budget */}
      {exceedsBudget && (
        <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-destructive">
          {t("lines.exceedsBudget")}
        </div>
      )}

      {/* Create/Edit Form */}
      {(showCreateForm || editingLine) && (
        <div className="rounded-lg border bg-card p-4 space-y-3">
          <div>
            <label htmlFor="line-name" className="block text-sm font-medium mb-1">{t("lines.nameLabel")}</label>
            <input
              id="line-name"
              type="text"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2"
              placeholder={t("lines.namePlaceholder")}
              aria-label={t("lines.nameAriaLabel")}
              disabled={isFormPending}
            />
          </div>
          <div>
            <label htmlFor="line-amount" className="block text-sm font-medium mb-1">
              {t("lines.approvedAmountLabel")}
            </label>
            <input
              id="line-amount"
              type="number"
              step="0.01"
              min="0"
              value={formAmount}
              onChange={(e) => setFormAmount(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2"
              placeholder="0.00"
              aria-label={t("lines.approvedAmountAriaLabel")}
              disabled={isFormPending}
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={editingLine ? handleUpdate : handleCreate}
              disabled={isFormPending}
              className="rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {editingLine ? tc("save") : tc("create")}
            </button>
            <button
              onClick={editingLine ? cancelEdit : cancelCreate}
              className="rounded-md border border-input px-4 py-2 hover:bg-muted"
            >
              {tc("cancel")}
            </button>
          </div>
        </div>
      )}

      {/* Table or Empty State */}
      {linesArray.length === 0 ? (
        <EmptyState
          title={t("lines.emptyTitle")}
          description={t("lines.emptyDescription")}
        />
      ) : (
        <div className="rounded-lg border">
          <table className="w-full">
            <thead className="border-b bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left font-medium">{t("table.name")}</th>
                <th className="px-4 py-3 text-right font-medium">
                  {t("table.approvedAmount")}
                </th>
                {canManage && (
                  <th className="px-4 py-3 text-left font-medium">{tc("actions")}</th>
                )}
              </tr>
            </thead>
            <tbody>
              {linesArray.map((line) => (
                <tr
                  key={line.id}
                  className="border-b transition-colors hover:bg-muted/50"
                >
                  <td className="px-4 py-3">{line.name}</td>
                  <td className="px-4 py-3 text-right font-mono">
                    {formatCurrency(line.approved_amount)}
                  </td>
                  {canManage && (
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <Link
                          href={`/budgets/${budgetId}/lines/${line.id}/executions`}
                          className="rounded-md border border-input px-3 py-1 text-sm hover:bg-muted"
                        >
                          {t("lines.viewExecutions")}
                        </Link>
                        <button
                          onClick={() => startEdit(line)}
                          className="rounded-md border border-input px-3 py-1 text-sm hover:bg-muted"
                        >
                          {tc("edit")}
                        </button>
                        <button
                          onClick={() => setDeleteLine(line)}
                          className="rounded-md border border-destructive bg-destructive px-3 py-1 text-sm text-destructive-foreground hover:bg-destructive/90"
                        >
                          {tc("delete")}
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Summary */}
      <div className="text-sm text-muted-foreground">
        {t("lines.total", {
          total: formatCurrency(totalLines),
          limit: formatCurrency(budgetLimit),
        })}
      </div>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={!!deleteLine}
        onOpenChange={(open) => !open && setDeleteLine(null)}
        title={t("lines.deleteConfirmTitle")}
        description={t("lines.deleteConfirmDescription", { name: deleteLine?.name ?? "" })}
        confirmLabel={tc("delete")}
        cancelLabel={tc("cancel")}
        onConfirm={handleDelete}
      />
    </div>
  );
}
