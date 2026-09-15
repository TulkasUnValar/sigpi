"use client";

/**
 * Advances TanStack Query hooks — project-scoped list and detail.
 *
 * All server data is scoped by the active institution and invalidated
 * after FSM mutations. The detail serializer carries nested reviews and
 * state logs, so the detail page needs a single query.
 */

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { useAuthStore } from "@/store/auth";
import type { AdvanceDetail, AdvanceDocument, AdvanceList, Page } from "@/features/advances/types";

export function useActiveInstitutionId(): string | null {
  return useAuthStore((s) => s.activeInstitution?.id ?? null);
}

/** Fetch the advances for a project (nested shortcut /projects/{id}/progress/). */
export function useAdvancesList(projectId: string) {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: queryKeys.advances.list(institutionId, projectId),
    queryFn: () =>
      api.get<Page<AdvanceList>>(`/api/projects/${projectId}/progress/`, {
        institutionId,
      }),
  });
}

/** Fetch a single advance's full detail (with nested reviews/state_logs). */
export function useAdvanceDetail(id: string) {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: queryKeys.advances.detail(institutionId, id),
    queryFn: () => api.get<AdvanceDetail>(`/api/progress/${id}/`, { institutionId }),
    // Only fetch once an id exists (RF-043 edit seeding).
    enabled: Boolean(id),
  });
}

/** Fetch the metadata-only documents of an advance (RF-042). */
export function useAdvanceDocuments(advanceId: string) {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: queryKeys.advances.documents(institutionId, advanceId),
    queryFn: () =>
      api.get<Page<AdvanceDocument>>(`/api/progress/${advanceId}/documents/`, {
        institutionId,
      }),
  });
}
