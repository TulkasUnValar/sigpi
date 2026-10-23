/**
 * BudgetDetail component — full detail view with tabs for lines, sources, attachments.
 *
 * Spec (budgets-ui):
 *   - Header with budget name, project, status badge.
 *   - Edit/Delete actions (role-gated).
 *   - Tabs: Overview (with BudgetSummary), Lines, Sources, Attachments.
 *   - Loading and error states.
 */

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useBudget } from "@/features/budgets/queries";
import { useDeleteBudget } from "@/features/budgets/mutations";
import { useBudgetPermissions } from "@/features/budgets/permissions";
import { BUDGET_STATUS_LABELS, formatCurrency } from "@/features/budgets/constants";
import { BudgetSummary } from "@/features/budgets/BudgetSummary";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Skeleton } from "@/components/shared/Skeleton";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { toast } from "sonner";
import type { BudgetStatus } from "@/features/budgets/types";

interface BudgetDetailProps {
  budgetId: string;
}

type TabKey = "overview" | "lines" | "sources" | "attachments";

export function BudgetDetail({ budgetId }: BudgetDetailProps) {
  const router = useRouter();
  const { data: budget, isLoading, error } = useBudget(budgetId);
  const deleteMutation = useDeleteBudget(budgetId);
  const { canManage } = useBudgetPermissions();
  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

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
        Error al cargar presupuesto: {(error as Error).message}
      </div>
    );
  }

  if (!budget) {
    return (
      <div className="rounded-lg border p-4">
        <p className="text-muted-foreground">Presupuesto no encontrado.</p>
      </div>
    );
  }

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync();
      toast.success("Presupuesto eliminado correctamente.");
      router.push("/budgets");
    } catch (error) {
      // Error already handled by mutation
      console.error("Error deleting budget:", error);
    }
  };

  const tabs: { key: TabKey; label: string }[] = [
    { key: "overview", label: "Resumen" },
    { key: "lines", label: "Líneas" },
    { key: "sources", label: "Fuentes" },
    { key: "attachments", label: "Adjuntos" },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link
            href="/budgets"
            className="mb-2 inline-block text-sm text-muted-foreground hover:text-foreground"
          >
            ← Volver a presupuestos
          </Link>
          <h1 className="text-3xl font-bold">{budget.name}</h1>
          <p className="mt-2 text-muted-foreground">Proyecto: {budget.project}</p>
          <div className="mt-2">
            <StatusBadge
              status={budget.status}
              label={BUDGET_STATUS_LABELS[budget.status as BudgetStatus]}
            />
          </div>
        </div>

        {canManage && (
          <div className="flex gap-2">
            <Link
              href={`/budgets/${budgetId}/edit`}
              className="rounded-md border border-input px-4 py-2 hover:bg-muted"
            >
              Editar
            </Link>
            <button
              onClick={() => setShowDeleteDialog(true)}
              className="rounded-md border border-destructive bg-destructive px-4 py-2 text-destructive-foreground hover:bg-destructive/90"
            >
              Eliminar
            </button>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b">
        <nav className="flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === "overview" && (
          <div className="space-y-6">
            {/* Budget Summary (IND-007/008/009) */}
            <BudgetSummary budgetId={budgetId} />

            {/* Budget Details */}
            <div className="rounded-lg border bg-card p-6">
              <h2 className="mb-4 text-xl font-semibold">Detalles del Presupuesto</h2>
              <dl className="grid grid-cols-2 gap-4">
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">Monto Aprobado</dt>
                  <dd className="mt-1 text-lg font-mono">
                    {formatCurrency(budget.approved_amount)}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">Estado</dt>
                  <dd className="mt-1">
                    <StatusBadge
                      status={budget.status}
                      label={BUDGET_STATUS_LABELS[budget.status as BudgetStatus]}
                    />
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">Creado</dt>
                  <dd className="mt-1 text-sm">
                    {new Date(budget.created_at).toLocaleString("es-CO")}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">Actualizado</dt>
                  <dd className="mt-1 text-sm">
                    {new Date(budget.updated_at).toLocaleString("es-CO")}
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        )}

        {activeTab === "lines" && (
          <div className="rounded-lg border bg-card p-6">
            <p className="text-muted-foreground">
              Gestión de líneas de presupuesto (PR2 - pendiente de implementar)
            </p>
          </div>
        )}

        {activeTab === "sources" && (
          <div className="rounded-lg border bg-card p-6">
            <p className="text-muted-foreground">
              Gestión de fuentes de financiamiento (PR2 - pendiente de implementar)
            </p>
          </div>
        )}

        {activeTab === "attachments" && (
          <div className="rounded-lg border bg-card p-6">
            <p className="text-muted-foreground">
              Gestión de adjuntos (PR2 - pendiente de implementar)
            </p>
          </div>
        )}
      </div>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        title="Eliminar presupuesto"
        description="¿Estás seguro de que deseas eliminar este presupuesto? Esta acción no se puede deshacer."
        confirmLabel="Eliminar"
        onConfirm={handleDelete}
      />
    </div>
  );
}
