"use client";

/**
 * Advances mutations — create and FSM transitions.
 *
 * Spec (server-state post-FSM invalidation):
 *   Every FSM mutation invalidates its resource and all derived queries
 *   (dashboard KPIs, detail, lists). After a director approves an advance,
 *   `advances`, `dashboard`, and `projects` keys refetch.
 *
 *   On mutation failure the cache is NOT invalidated and the error is shown.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useActiveInstitutionId } from "@/features/advances/queries";
import type { AdvanceDetail, CreateAdvancePayload } from "@/features/advances/types";

/** Invalidate every query derived from the advances resource. */
function invalidateAdvances(qc: ReturnType<typeof useQueryClient>) {
  void qc.invalidateQueries({ queryKey: ["advances"] });
  void qc.invalidateQueries({ queryKey: ["dashboard"] });
  void qc.invalidateQueries({ queryKey: ["projects"] });
}

/** Create an advance and invalidate the advances/dashboard/projects caches. */
export function useCreateAdvance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateAdvancePayload) =>
      api.post<AdvanceDetail>("/api/progress/", payload),
    onSuccess: () => invalidateAdvances(qc),
  });
}

/**
 * Trigger an advance FSM transition. `action` is the DRF endpoint action
 * (e.g. "approve", "reject"). On success all derived caches invalidate.
 */
export function useAdvanceTransition() {
  const qc = useQueryClient();
  const institutionId = useActiveInstitutionId();
  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) =>
      api.post<AdvanceDetail>(`/api/progress/${id}/${action}/`, {}, {
        institutionId,
      }),
    onSuccess: () => invalidateAdvances(qc),
  });
}