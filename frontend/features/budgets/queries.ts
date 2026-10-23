/**
 * Budgets queries — TanStack Query hooks for reading budget data.
 *
 * Follows the same pattern as calls/queries.ts:
 * - All queries are scoped by activeInstitution
 * - Queries use the queryKeys factory
 * - Errors are handled via onError callback
 */

import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@/store/auth";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type {
  Budget,
  BudgetAttachment,
  BudgetExecution,
  BudgetFilter,
  BudgetLine,
  BudgetListItem,
  BudgetSummary,
  FundingSource,
  Page,
} from "./types";

/** Hook: List budgets with optional filters. */
export const useBudgets = (filters: BudgetFilter = {}) => {
  const institutionId = useAuthStore((state) => state.activeInstitution?.id ?? null);

  return useQuery({
    queryKey: queryKeys.budgets.list(institutionId, filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.project) params.append("project", filters.project);
      if (filters.status) params.append("status", filters.status);

      const queryString = params.toString();
      const url = queryString ? `/api/budgets/?${queryString}` : "/api/budgets/";
      const response = await api.get<Page<BudgetListItem>>(url);
      return response;
    },
    enabled: !!institutionId,
  });
};

/** Hook: Get a single budget by ID. */
export const useBudget = (id: string) => {
  const institutionId = useAuthStore((state) => state.activeInstitution?.id ?? null);

  return useQuery({
    queryKey: queryKeys.budgets.detail(institutionId, id),
    queryFn: async () => {
      const response = await api.get<Budget>(`/api/budgets/${id}/`);
      return response;
    },
    enabled: !!institutionId && !!id,
  });
};

/** Hook: Get budget lines for a budget. */
export const useBudgetLines = (budgetId: string) => {
  const institutionId = useAuthStore((state) => state.activeInstitution?.id ?? null);

  return useQuery({
    queryKey: queryKeys.budgets.lines(institutionId, budgetId),
    queryFn: async () => {
      const response = await api.get<Page<BudgetLine>>(
        `/api/budgets/${budgetId}/lines/`
      );
      return response.results;
    },
    enabled: !!institutionId && !!budgetId,
  });
};

/** Hook: Get executions for a budget line. */
export const useBudgetExecutions = (budgetId: string, lineId: string) => {
  const institutionId = useAuthStore((state) => state.activeInstitution?.id ?? null);

  return useQuery({
    queryKey: queryKeys.budgets.executions(institutionId, budgetId, lineId),
    queryFn: async () => {
      const response = await api.get<Page<BudgetExecution>>(
        `/api/budgets/${budgetId}/lines/${lineId}/executions/`
      );
      return response.results;
    },
    enabled: !!institutionId && !!budgetId && !!lineId,
  });
};

/** Hook: Get funding sources for a project. */
export const useFundingSources = (projectId: string) => {
  const institutionId = useAuthStore((state) => state.activeInstitution?.id ?? null);

  return useQuery({
    queryKey: queryKeys.budgets.sources(institutionId, projectId),
    queryFn: async () => {
      const response = await api.get<Page<FundingSource>>(
        `/api/projects/${projectId}/funding-sources/`
      );
      return response.results;
    },
    enabled: !!institutionId && !!projectId,
  });
};

/** Hook: Get attachments for a budget. */
export const useBudgetAttachments = (budgetId: string) => {
  const institutionId = useAuthStore((state) => state.activeInstitution?.id ?? null);

  return useQuery({
    queryKey: queryKeys.budgets.attachments(institutionId, budgetId),
    queryFn: async () => {
      const response = await api.get<Page<BudgetAttachment>>(
        `/api/budgets/${budgetId}/attachments/`
      );
      return response.results;
    },
    enabled: !!institutionId && !!budgetId,
  });
};

/** Hook: Get budget summary (IND-007/008/009). */
export const useBudgetSummary = (budgetId: string) => {
  const institutionId = useAuthStore((state) => state.activeInstitution?.id ?? null);

  return useQuery({
    queryKey: queryKeys.budgets.summary(institutionId, budgetId),
    queryFn: async () => {
      const response = await api.get<BudgetSummary>(
        `/api/budgets/${budgetId}/summary/`
      );
      return response;
    },
    enabled: !!institutionId && !!budgetId,
  });
};
