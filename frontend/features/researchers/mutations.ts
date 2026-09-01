"use client";

/**
 * Researchers mutations — create, patch, and deactivate.
 *
 * Spec (researchers-ui):
 *   - POST  /api/researchers/            create (director+, level ≤ 3)
 *   - PATCH /api/researchers/{id}/       update (self or admin+); reactivation
 *                                        is an edit PATCH with is_active:true
 *   - POST  /api/researchers/{id}/deactivate/  admin+ (level ≤ 2)
 *
 * Design: every mutation passes the active institutionId so the tenant
 * header is sent, and invalidates `researchers.all` ONLY on success.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import type {
  CreateResearcherPayload,
  Researcher,
  UpdateResearcherPayload,
} from "@/features/researchers/types";

/** Invalidate every query derived from the researchers resource. */
function invalidateResearchers(qc: ReturnType<typeof useQueryClient>) {
  void qc.invalidateQueries({ queryKey: ["researchers"] });
}

function useInstitutionId(): string | null {
  return useAuthStore((s) => s.activeInstitution?.id ?? null);
}

/** Create a researcher — POST /api/researchers/. */
export function useCreateResearcher() {
  const qc = useQueryClient();
  const institutionId = useInstitutionId();
  return useMutation({
    mutationFn: (payload: CreateResearcherPayload) =>
      api.post<Researcher>("/api/researchers/", payload, { institutionId }),
    onSuccess: () => invalidateResearchers(qc),
  });
}

/**
 * Update a researcher — PATCH /api/researchers/{id}/.
 * Passing `is_active: true` reactivates (no activate endpoint exists).
 */
export function useUpdateResearcher(id: string) {
  const qc = useQueryClient();
  const institutionId = useInstitutionId();
  return useMutation({
    mutationFn: (payload: UpdateResearcherPayload) =>
      api.patch<Researcher>(`/api/researchers/${id}/`, payload, { institutionId }),
    onSuccess: () => invalidateResearchers(qc),
  });
}

/** Deactivate a researcher — POST /api/researchers/{id}/deactivate/ (admin+). */
export function useDeactivateResearcher() {
  const qc = useQueryClient();
  const institutionId = useInstitutionId();
  return useMutation({
    mutationFn: (id: string) =>
      api.post<Researcher>(`/api/researchers/${id}/deactivate/`, {}, { institutionId }),
    onSuccess: () => invalidateResearchers(qc),
  });
}
