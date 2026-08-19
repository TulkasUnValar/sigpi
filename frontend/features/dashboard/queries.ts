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
    queryFn: () =>
      api.get<Page<ProjectSummary>>("/api/projects/", { institutionId }),
  });
}

/** Fetch the progress (advances) list (first page) for the active institution. */
export function useProgressList() {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: queryKeys.dashboard.progress(institutionId),
    queryFn: () =>
      api.get<Page<ProgressSummary>>("/api/progress/", { institutionId }),
  });
}