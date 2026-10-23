/**
 * BudgetForm component — shared form for create/edit budget.
 *
 * Spec (budgets-ui):
 *   - RHF + zod validation for name, approved_amount, project.
 *   - Decimal field with proper formatting.
 *   - Project selector (dropdown).
 *   - Error handling with toast notifications.
 *   - Redirect on success.
 */

"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { budgetFormSchema, type BudgetFormValues, buildCreateBudgetPayload } from "@/features/budgets/schemas";
import { useCreateBudget, useUpdateBudget } from "@/features/budgets/mutations";
import { useProjectsList } from "@/features/projects/queries";
import { formatCurrency } from "@/features/budgets/constants";
import type { Budget } from "@/features/budgets/types";

interface BudgetFormProps {
  budget?: Budget;
  mode: "create" | "edit";
}

export function BudgetForm({ budget, mode }: BudgetFormProps) {
  const router = useRouter();
  const createMutation = useCreateBudget();
  const updateMutation = useUpdateBudget(budget?.id ?? "");
  const { data: projectsData } = useProjectsList();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setValue,
  } = useForm<BudgetFormValues>({
    resolver: zodResolver(budgetFormSchema),
    defaultValues: {
      project: budget?.project ?? "",
      name: budget?.name ?? "",
      approved_amount: budget?.approved_amount ?? "0.00",
    },
  });

  useEffect(() => {
    if (budget && mode === "edit") {
      setValue("project", budget.project);
      setValue("name", budget.name);
      setValue("approved_amount", budget.approved_amount);
    }
  }, [budget, mode, setValue]);

  const onSubmit = async (data: BudgetFormValues) => {
    try {
      if (mode === "create") {
        const payload = buildCreateBudgetPayload(data);
        const newBudget = await createMutation.mutateAsync(payload);
        router.push(`/budgets/${newBudget.id}`);
      } else if (budget) {
        await updateMutation.mutateAsync({
          name: data.name,
          approved_amount: data.approved_amount,
        });
        router.push(`/budgets/${budget.id}`);
      }
    } catch (error) {
      // Error already handled by mutation
      console.error("Error saving budget:", error);
    }
  };

  const projects = projectsData?.results ?? [];
  const isSubmittingForm = isSubmitting || createMutation.isPending || updateMutation.isPending;

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* Project selector (only for create) */}
      {mode === "create" && (
        <div>
          <label htmlFor="project" className="mb-2 block text-sm font-medium">
            Proyecto *
          </label>
          <select
            id="project"
            {...register("project")}
            className="w-full rounded-md border border-input bg-background px-3 py-2"
            disabled={isSubmittingForm}
          >
            <option value="">Selecciona un proyecto</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title}
              </option>
            ))}
          </select>
          {errors.project && (
            <p className="mt-1 text-sm text-destructive">{errors.project.message}</p>
          )}
        </div>
      )}

      {/* Project display (for edit mode) */}
      {mode === "edit" && budget && (
        <div>
          <label className="mb-2 block text-sm font-medium">Proyecto</label>
          <p className="rounded-md border border-input bg-muted px-3 py-2">
            {projects.find((p) => p.id === budget.project)?.title ?? budget.project}
          </p>
        </div>
      )}

      {/* Name */}
      <div>
        <label htmlFor="name" className="mb-2 block text-sm font-medium">
          Nombre *
        </label>
        <input
          id="name"
          type="text"
          {...register("name")}
          className="w-full rounded-md border border-input bg-background px-3 py-2"
          placeholder="Ej: Presupuesto 2026"
          disabled={isSubmittingForm}
        />
        {errors.name && (
          <p className="mt-1 text-sm text-destructive">{errors.name.message}</p>
        )}
      </div>

      {/* Approved Amount */}
      <div>
        <label htmlFor="approved_amount" className="mb-2 block text-sm font-medium">
          Monto Aprobado *
        </label>
        <input
          id="approved_amount"
          type="text"
          {...register("approved_amount")}
          className="w-full rounded-md border border-input bg-background px-3 py-2 font-mono"
          placeholder="0.00"
          disabled={isSubmittingForm}
        />
        {errors.approved_amount && (
          <p className="mt-1 text-sm text-destructive">{errors.approved_amount.message}</p>
        )}
        <p className="mt-1 text-xs text-muted-foreground">
          Formato: {formatCurrency("10000.00")}
        </p>
      </div>

      {/* Actions */}
      <div className="flex gap-4">
        <button
          type="submit"
          disabled={isSubmittingForm}
          className="rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {isSubmittingForm
            ? "Guardando..."
            : mode === "create"
              ? "Crear presupuesto"
              : "Guardar cambios"}
        </button>
        <button
          type="button"
          onClick={() => router.back()}
          disabled={isSubmittingForm}
          className="rounded-md border border-input px-4 py-2 hover:bg-muted"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
