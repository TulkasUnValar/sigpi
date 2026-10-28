/**
 * Budgets mutations — TanStack Query hooks for creating, updating, and deleting budget data.
 *
 * Follows the same pattern as calls/mutations.ts:
 * - All mutations invalidate relevant queries on success
 * - Errors are handled via onError callback
 * - Optimistic updates are NOT used (server is authoritative)
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { toast } from "sonner";
import type {
  Budget,
  BudgetAttachment,
  BudgetExecution,
  BudgetLine,
  CreateBudgetAttachmentPayload,
  CreateBudgetExecutionPayload,
  CreateBudgetLinePayload,
  CreateBudgetPayload,
  CreateFundingSourcePayload,
  FundingSource,
  UpdateBudgetAttachmentPayload,
  UpdateBudgetLinePayload,
  UpdateBudgetPayload,
  UpdateFundingSourcePayload,
} from "./types";

/** Hook: Create a new budget. */
export const useCreateBudget = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: CreateBudgetPayload) => {
      const response = await api.post<Budget>("/api/budgets/", payload);
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.budgets.lists() });
      toast.success("Presupuesto creado correctamente.");
    },
    onError: (error: Error & { status?: number }) => {
      toast.error(error.message || "Error al crear el presupuesto.");
    },
  });
};

/** Hook: Update a budget. */
export const useUpdateBudget = (budgetId: string) => {
  const queryClient = useQueryClient();
  const institutionId = useAuthStore((state) => state.activeInstitution?.id ?? null);

  return useMutation({
    mutationFn: async (payload: UpdateBudgetPayload) => {
      const response = await api.patch<Budget>(`/api/budgets/${budgetId}/`, payload);
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.budgets.detail(institutionId, budgetId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.budgets.lists() });
      toast.success("Presupuesto actualizado correctamente.");
    },
    onError: (error: Error & { status?: number }) => {
      toast.error(error.message || "Error al actualizar el presupuesto.");
    },
  });
};

/** Hook: Delete a budget. */
export const useDeleteBudget = (budgetId: string) => {
  const queryClient = useQueryClient();
  const institutionId = useAuthStore((state) => state.activeInstitution?.id ?? null);

  return useMutation({
    mutationFn: async () => {
      await api.delete(`/api/budgets/${budgetId}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.budgets.lists() });
      queryClient.removeQueries({ queryKey: queryKeys.budgets.detail(institutionId, budgetId) });
      toast.success("Presupuesto eliminado correctamente.");
    },
    onError: (error: Error & { status?: number }) => {
      toast.error(error.message || "Error al eliminar el presupuesto.");
    },
  });
};

/** Hook: Create a budget line. */
export const useCreateBudgetLine = (budgetId: string) => {
  const queryClient = useQueryClient();
  const institutionId = useAuthStore((state) => state.activeInstitution?.id ?? null);

  return useMutation({
    mutationFn: async (payload: CreateBudgetLinePayload) => {
      const response = await api.post<BudgetLine>(
        `/api/budgets/${budgetId}/lines/`,
        payload
      );
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.budgets.lines(institutionId, budgetId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.budgets.detail(institutionId, budgetId),
      });
      toast.success("Rubro creado correctamente.");
    },
    onError: (error: Error & { status?: number }) => {
      toast.error(error.message || "Error al crear el rubro.");
    },
  });
};

/** Hook: Update a budget line. */
export const useUpdateBudgetLine = (budgetId: string, lineId: string) => {
  const queryClient = useQueryClient();
  const institutionId = useAuthStore((state) => state.activeInstitution?.id ?? null);

  return useMutation({
    mutationFn: async (payload: UpdateBudgetLinePayload) => {
      const response = await api.patch<BudgetLine>(
        `/api/budgets/${budgetId}/lines/${lineId}/`,
        payload
      );
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.budgets.lines(institutionId, budgetId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.budgets.detail(institutionId, budgetId),
      });
      toast.success("Rubro actualizado correctamente.");
    },
    onError: (error: Error & { status?: number }) => {
      toast.error(error.message || "Error al actualizar el rubro.");
    },
  });
};

/** Hook: Delete a budget line. */
export const useDeleteBudgetLine = (budgetId: string) => {
  const queryClient = useQueryClient();
  const institutionId = useAuthStore((state) => state.activeInstitution?.id ?? null);

  return useMutation({
    mutationFn: async (lineId: string) => {
      await api.delete(`/api/budgets/${budgetId}/lines/${lineId}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.budgets.lines(institutionId, budgetId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.budgets.detail(institutionId, budgetId),
      });
      toast.success("Rubro eliminado correctamente.");
    },
    onError: (error: Error & { status?: number }) => {
      toast.error(error.message || "Error al eliminar el rubro.");
    },
  });
};

/** Hook: Create a funding source for a project. */
export const useCreateFundingSource = (projectId: string) => {
  const queryClient = useQueryClient();
  const institutionId = useAuthStore((state) => state.activeInstitution?.id ?? null);

  return useMutation({
    mutationFn: async (payload: CreateFundingSourcePayload) => {
      const response = await api.post<FundingSource>(
        `/api/projects/${projectId}/funding-sources/`,
        payload
      );
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.budgets.sources(institutionId, projectId),
      });
      toast.success("Fuente de financiación creada correctamente.");
    },
    onError: (error: Error & { status?: number }) => {
      toast.error(error.message || "Error al crear la fuente de financiación.");
    },
  });
};

/** Hook: Update a funding source. */
export const useUpdateFundingSource = (projectId: string, sourceId: string) => {
  const queryClient = useQueryClient();
  const institutionId = useAuthStore((state) => state.activeInstitution?.id ?? null);

  return useMutation({
    mutationFn: async (payload: UpdateFundingSourcePayload) => {
      const response = await api.patch<FundingSource>(
        `/api/projects/${projectId}/funding-sources/${sourceId}/`,
        payload
      );
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.budgets.sources(institutionId, projectId),
      });
      toast.success("Fuente de financiación actualizada correctamente.");
    },
    onError: (error: Error & { status?: number }) => {
      toast.error(error.message || "Error al actualizar la fuente de financiación.");
    },
  });
};

/** Hook: Delete a funding source. */
export const useDeleteFundingSource = (projectId: string) => {
  const queryClient = useQueryClient();
  const institutionId = useAuthStore((state) => state.activeInstitution?.id ?? null);

  return useMutation({
    mutationFn: async (sourceId: string) => {
      await api.delete(`/api/projects/${projectId}/funding-sources/${sourceId}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.budgets.sources(institutionId, projectId),
      });
      toast.success("Fuente de financiación eliminada correctamente.");
    },
    onError: (error: Error & { status?: number }) => {
      toast.error(error.message || "Error al eliminar la fuente de financiación.");
    },
  });
};

/** Hook: Create a budget execution. */
export const useCreateBudgetExecution = (budgetId: string, lineId: string) => {
  const queryClient = useQueryClient();
  const institutionId = useAuthStore((state) => state.activeInstitution?.id ?? null);

  return useMutation({
    mutationFn: async (payload: CreateBudgetExecutionPayload) => {
      const response = await api.post<BudgetExecution>(
        `/api/budgets/${budgetId}/lines/${lineId}/executions/`,
        payload
      );
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.budgets.executions(institutionId, budgetId, lineId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.budgets.summary(institutionId, budgetId),
      });
      toast.success("Ejecución registrada correctamente.");
    },
    onError: (error: Error & { status?: number }) => {
      // RN-020: over-execution without authorization
      if (error.status === 400) {
        toast.error("La ejecución excede el presupuesto aprobado del rubro.");
      } else {
        toast.error(error.message || "Error al registrar la ejecución.");
      }
    },
  });
};

/** Hook: Create a budget attachment. */
export const useCreateBudgetAttachment = (budgetId: string) => {
  const queryClient = useQueryClient();
  const institutionId = useAuthStore((state) => state.activeInstitution?.id ?? null);

  return useMutation({
    mutationFn: async (payload: CreateBudgetAttachmentPayload) => {
      const response = await api.post<BudgetAttachment>(
        `/api/budgets/${budgetId}/attachments/`,
        payload
      );
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.budgets.attachments(institutionId, budgetId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.budgets.detail(institutionId, budgetId),
      });
      toast.success("Adjunto creado correctamente.");
    },
    onError: (error: Error & { status?: number }) => {
      toast.error(error.message || "Error al crear el adjunto.");
    },
  });
};

/** Hook: Update a budget attachment. */
export const useUpdateBudgetAttachment = (budgetId: string, attachmentId: string) => {
  const queryClient = useQueryClient();
  const institutionId = useAuthStore((state) => state.activeInstitution?.id ?? null);

  return useMutation({
    mutationFn: async (payload: UpdateBudgetAttachmentPayload) => {
      const response = await api.patch<BudgetAttachment>(
        `/api/budgets/${budgetId}/attachments/${attachmentId}/`,
        payload
      );
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.budgets.attachments(institutionId, budgetId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.budgets.detail(institutionId, budgetId),
      });
      toast.success("Adjunto actualizado correctamente.");
    },
    onError: (error: Error & { status?: number }) => {
      toast.error(error.message || "Error al actualizar el adjunto.");
    },
  });
};

/** Hook: Delete a budget attachment. */
export const useDeleteBudgetAttachment = (budgetId: string) => {
  const queryClient = useQueryClient();
  const institutionId = useAuthStore((state) => state.activeInstitution?.id ?? null);

  return useMutation({
    mutationFn: async (attachmentId: string) => {
      await api.delete(`/api/budgets/${budgetId}/attachments/${attachmentId}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.budgets.attachments(institutionId, budgetId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.budgets.detail(institutionId, budgetId),
      });
      toast.success("Adjunto eliminado correctamente.");
    },
    onError: (error: Error & { status?: number }) => {
      toast.error(error.message || "Error al eliminar el adjunto.");
    },
  });
};
