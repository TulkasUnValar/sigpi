"use client";

/**
 * Institutions mutations — root CRUD + FSM lifecycle transitions.
 *
 * Spec (institutions-ui RF-F02/RF-F04):
 *   - POST   /api/institutions/                  create root institution
 *   - PATCH  /api/institutions/{id}/             update root institution
 *   - DELETE /api/institutions/{id}/             delete root institution
 *   - POST   /api/institutions/{id}/{action}/    FSM transition (activate/deactivate/archive)
 *
 * Design (institutions):
 *   - The Institution is the root entity: calls MUST NOT send the
 *     X-Institution-ID header (sendInstitutionId: false).
 *   - Mutations invalidate `institutions.all` ONLY on success; a failed
 *     mutation never touches the cache (spec: no optimistic updates).
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  CreateInstitutionPayload,
  Institution,
  UpdateInstitutionPayload,
} from "@/features/institutions/types";

/** Invalidate every query derived from the institutions resource. */
function invalidateInstitutions(qc: ReturnType<typeof useQueryClient>) {
  void qc.invalidateQueries({ queryKey: ["institutions"] });
}

/** Create a root institution (superadmin only — backend IsSuperAdmin). */
export function useCreateInstitution() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateInstitutionPayload) =>
      api.post<Institution>("/api/institutions/", payload, {
        sendInstitutionId: false,
      }),
    onSuccess: () => invalidateInstitutions(qc),
  });
}

/** Update a root institution (PATCH — partial update). */
export function useUpdateInstitution(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: UpdateInstitutionPayload) =>
      api.patch<Institution>(`/api/institutions/${id}/`, payload, {
        sendInstitutionId: false,
      }),
    onSuccess: () => invalidateInstitutions(qc),
  });
}

/** Delete a root institution. */
export function useDeleteInstitution() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete<void>(`/api/institutions/${id}/`, {
        sendInstitutionId: false,
      }),
    onSuccess: () => invalidateInstitutions(qc),
  });
}

/**
 * Trigger an institution FSM transition. `action` is the DRF endpoint
 * action (activate | deactivate | archive). On success the whole
 * institutions cache invalidates so tree/detail refetch.
 */
export function useInstitutionTransition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) =>
      api.post<Institution>(
        `/api/institutions/${id}/${action}/`,
        {},
        {
          sendInstitutionId: false,
        },
      ),
    onSuccess: () => invalidateInstitutions(qc),
  });
}
