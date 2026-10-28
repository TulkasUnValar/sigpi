/**
 * FundingSourcesManager component — CRUD for funding sources.
 *
 * Spec (PR2):
 *   - Table with columns: Nombre, Monto, Acciones (edit/delete).
 *   - Inline form for create/edit (name + amount inputs).
 *   - Coverage calculation: (total / budgetApprovedAmount) * 100.
 *   - Show coverage % if < 100%.
 *   - Role-gated: only canManage can see create/edit/delete.
 *   - ConfirmDialog for delete.
 *   - Toast success/error.
 *   - EmptyState if no sources.
 *   - Skeleton while loading.
 */

"use client";

import { useState, useMemo } from "react";
import { useFundingSources } from "@/features/budgets/queries";
import {
  useCreateFundingSource,
  useUpdateFundingSource,
  useDeleteFundingSource,
} from "@/features/budgets/mutations";
import { useBudgetPermissions } from "@/features/budgets/permissions";
import { formatCurrency, parseDecimal } from "@/features/budgets/constants";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { toast } from "sonner";
import type { FundingSource } from "@/features/budgets/types";

interface FundingSourcesManagerProps {
  projectId: string;
  budgetApprovedAmount: string;
}

export function FundingSourcesManager({
  projectId,
  budgetApprovedAmount,
}: FundingSourcesManagerProps) {
  const { data: sources, isLoading, error } = useFundingSources(projectId);
  const createMutation = useCreateFundingSource(projectId);
  const { canManage } = useBudgetPermissions();

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingSource, setEditingSource] = useState<FundingSource | null>(null);
  const [deleteSource, setDeleteSource] = useState<FundingSource | null>(null);

  // Form state
  const [formName, setFormName] = useState("");
  const [formAmount, setFormAmount] = useState("");

  // Hooks for update/delete
  const updateMutation = useUpdateFundingSource(projectId, editingSource?.id ?? "");
  const deleteMutation = useDeleteFundingSource(projectId);

  const sourcesArray = useMemo(() => sources ?? [], [sources]);
  const totalSources = useMemo(
    () => sourcesArray.reduce((sum, source) => sum + parseDecimal(source.amount), 0),
    [sourcesArray]
  );

  if (isLoading) {
    return <Skeleton className="h-64 w-full" />;
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-destructive">
        Error al cargar fuentes: {(error as Error).message}
      </div>
    );
  }

  const budgetLimit = parseDecimal(budgetApprovedAmount);
  const coverage = budgetLimit > 0 ? (totalSources / budgetLimit) * 100 : 0;
  const showCoverage = coverage < 100;

  const validateAmount = (value: string): boolean => {
    const num = parseFloat(value);
    return !isNaN(num) && num >= 0;
  };

  const handleCreate = async () => {
    if (!formName.trim() || !formAmount.trim()) {
      toast.error("Complete todos los campos.");
      return;
    }

    if (!validateAmount(formAmount)) {
      toast.error("El monto debe ser un número válido mayor o igual a 0.");
      return;
    }

    try {
      await createMutation.mutateAsync({
        name: formName.trim(),
        amount: formAmount.trim(),
      });
      setFormName("");
      setFormAmount("");
      setShowCreateForm(false);
    } catch (error) {
      console.error("Error creating source:", error);
    }
  };

  const handleUpdate = async () => {
    if (!editingSource) return;
    if (!formName.trim() || !formAmount.trim()) {
      toast.error("Complete todos los campos.");
      return;
    }

    if (!validateAmount(formAmount)) {
      toast.error("El monto debe ser un número válido mayor o igual a 0.");
      return;
    }

    try {
      await updateMutation.mutateAsync({
        name: formName.trim(),
        amount: formAmount.trim(),
      });
      setEditingSource(null);
      setFormName("");
      setFormAmount("");
    } catch (error) {
      console.error("Error updating source:", error);
    }
  };

  const handleDelete = async () => {
    if (!deleteSource) return;
    try {
      await deleteMutation.mutateAsync(deleteSource.id);
      setDeleteSource(null);
    } catch (error) {
      console.error("Error deleting source:", error);
    }
  };

  const startEdit = (source: FundingSource) => {
    setEditingSource(source);
    setFormName(source.name);
    setFormAmount(source.amount);
    setShowCreateForm(false);
  };

  const cancelEdit = () => {
    setEditingSource(null);
    setFormName("");
    setFormAmount("");
  };

  const startCreate = () => {
    setEditingSource(null);
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
        <h2 className="text-xl font-semibold">Fuentes de Financiamiento</h2>
        {canManage && !showCreateForm && !editingSource && (
          <button
            onClick={startCreate}
            className="rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90"
          >
            Agregar fuente
          </button>
        )}
      </div>

      {/* Coverage info */}
      {showCoverage && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-blue-900">
          Cobertura: {coverage.toFixed(2)}%
        </div>
      )}

      {/* Create/Edit Form */}
      {(showCreateForm || editingSource) && (
        <div className="rounded-lg border bg-card p-4 space-y-3">
          <div>
            <label htmlFor="source-name" className="block text-sm font-medium mb-1">Nombre</label>
            <input
              id="source-name"
              type="text"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2"
              placeholder="Nombre de la fuente"
              aria-label="Nombre de la fuente de financiamiento"
              disabled={isFormPending}
            />
          </div>
          <div>
            <label htmlFor="source-amount" className="block text-sm font-medium mb-1">Monto</label>
            <input
              id="source-amount"
              type="number"
              step="0.01"
              min="0"
              value={formAmount}
              onChange={(e) => setFormAmount(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2"
              placeholder="0.00"
              aria-label="Monto de la fuente de financiamiento"
              disabled={isFormPending}
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={editingSource ? handleUpdate : handleCreate}
              disabled={isFormPending}
              className="rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {editingSource ? "Guardar" : "Crear"}
            </button>
            <button
              onClick={editingSource ? cancelEdit : cancelCreate}
              className="rounded-md border border-input px-4 py-2 hover:bg-muted"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {/* Table or Empty State */}
      {sourcesArray.length === 0 ? (
        <EmptyState
          title="No hay fuentes"
          description="Aún no se han creado fuentes de financiamiento."
        />
      ) : (
        <div className="rounded-lg border">
          <table className="w-full">
            <thead className="border-b bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Nombre</th>
                <th className="px-4 py-3 text-right font-medium">Monto</th>
                {canManage && (
                  <th className="px-4 py-3 text-left font-medium">Acciones</th>
                )}
              </tr>
            </thead>
            <tbody>
              {sourcesArray.map((source) => (
                <tr
                  key={source.id}
                  className="border-b transition-colors hover:bg-muted/50"
                >
                  <td className="px-4 py-3">{source.name}</td>
                  <td className="px-4 py-3 text-right font-mono">
                    {formatCurrency(source.amount)}
                  </td>
                  {canManage && (
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button
                          onClick={() => startEdit(source)}
                          className="rounded-md border border-input px-3 py-1 text-sm hover:bg-muted"
                        >
                          Editar
                        </button>
                        <button
                          onClick={() => setDeleteSource(source)}
                          className="rounded-md border border-destructive bg-destructive px-3 py-1 text-sm text-destructive-foreground hover:bg-destructive/90"
                        >
                          Eliminar
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
        Total: {formatCurrency(totalSources)} de {formatCurrency(budgetLimit)}
      </div>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={!!deleteSource}
        onOpenChange={(open) => !open && setDeleteSource(null)}
        title="Eliminar fuente"
        description={`¿Estás seguro de que deseas eliminar "${deleteSource?.name}"? Esta acción no se puede deshacer.`}
        confirmLabel="Eliminar"
        cancelLabel="Cancelar"
        onConfirm={handleDelete}
      />
    </div>
  );
}
