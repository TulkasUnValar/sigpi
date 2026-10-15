"use client";

/**
 * Dashboard TanStack Query hooks — compose KPIs from /projects/ and
 * /progress/ list endpoints, scoped by active institution.
 */

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { useAuthStore } from "@/store/auth";
import type { ProjectSummary, ProgressSummary } from "@/features/dashboard/kpi-selectors";

/** DRF paginated envelope. */
export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

function useActiveInstitutionId(): string | null {
  return useAuthStore((s) => s.activeInstitution?.id ?? null);
}

/** Fetch the projects list (first page) for the active institution. */
export function useProjectsList() {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: queryKeys.dashboard.projects(institutionId),
    queryFn: () => api.get<Page<ProjectSummary>>("/api/projects/", { institutionId }),
  });
}

/** Fetch the progress (advances) list (first page) for the active institution. */
export function useProgressList() {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: queryKeys.dashboard.progress(institutionId),
    queryFn: () => api.get<Page<ProgressSummary>>("/api/progress/", { institutionId }),
  });
}

export interface DashboardSummary {
  indicators: {
    "IND-001": number;
    "IND-002": Array<{ center_id: string; name: string; count: number }>;
    "IND-003": Array<{ status: string; count: number }>;
    "IND-004": number;
    "IND-005": number;
    "IND-006": number;
    "IND-007": string;
    "IND-008": string;
    "IND-009": string;
    "IND-010": Array<{ project_id: string; name: string; count: number }>;
    "IND-011": Array<{ researcher_id: string; full_name: string; count: number }>;
    "IND-012": { total: number; complete: number; rate: number };
    "IND-013": number;
    "IND-014": number;
  };
  charts: {
    projects_by_status: Array<{ status: string; count: number }>;
    projects_by_center: Array<{ center_id: string; name: string; count: number }>;
    budget: { approved: string; executed: string; balance: string };
    progress_reports: { pending: number; observed: number; approved: number };
  };
}

/** Fetch the pre-computed dashboard summary (indicators + charts). */
export function useDashboardSummary() {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: queryKeys.dashboard.summary(institutionId),
    queryFn: () => api.get<DashboardSummary>("/api/dashboard/summary/", { institutionId }),
    enabled: !!institutionId,
  });
}
