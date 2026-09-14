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
import type {
  AdvanceDetail,
  AdvanceDocument,
  AdvanceDocumentPayload,
  CreateAdvancePayload,
} from "@/features/advances/types";

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

/** Payload for an advance FSM transition (RF-041). */
export interface AdvanceTransitionPayload {
  id: string;
  action: string;
  /** Required by observe/reject; omitted for the other transitions. */
  review_text?: string;
}

/**
 * Trigger an advance FSM transition. `action` is the DRF endpoint action
 * (e.g. "approve", "reject"). observe/reject send `{ review_text }` in the
 * body (RF-041); the other transitions keep the empty body. On success all
 * derived caches invalidate.
 */
export function useAdvanceTransition() {
  const qc = useQueryClient();
  const institutionId = useActiveInstitutionId();
  return useMutation({
    mutationFn: ({ id, action, review_text }: AdvanceTransitionPayload) =>
      api.post<AdvanceDetail>(
        `/api/progress/${id}/${action}/`,
        review_text ? { review_text } : {},
        { institutionId },
      ),
    onSuccess: () => invalidateAdvances(qc),
  });
}

// ── Nested documents ────────────────────────────────────

/** Create a document under an advance and invalidate the advances cache (RF-042). */
export function useCreateAdvanceDocument() {
  const qc = useQueryClient();
  const institutionId = useActiveInstitutionId();
  return useMutation({
    mutationFn: ({ advanceId, ...payload }: { advanceId: string } & AdvanceDocumentPayload) =>
      api.post<AdvanceDocument>(`/api/progress/${advanceId}/documents/`, payload, {
        institutionId,
      }),
    onSuccess: () => invalidateAdvances(qc),
  });
}

/** Update a document's metadata and invalidate the advances cache (RF-042). */
export function useUpdateAdvanceDocument() {
  const qc = useQueryClient();
  const institutionId = useActiveInstitutionId();
  return useMutation({
    mutationFn: ({
      advanceId,
      documentId,
      ...payload
    }: { advanceId: string; documentId: string } & AdvanceDocumentPayload) =>
      api.patch<AdvanceDocument>(`/api/progress/${advanceId}/documents/${documentId}/`, payload, {
        institutionId,
      }),
    onSuccess: () => invalidateAdvances(qc),
  });
}

/** Delete a document and invalidate the advances cache (RF-042). */
export function useDeleteAdvanceDocument() {
  const qc = useQueryClient();
  const institutionId = useActiveInstitutionId();
  return useMutation({
    mutationFn: ({ advanceId, documentId }: { advanceId: string; documentId: string }) =>
      api.delete<void>(`/api/progress/${advanceId}/documents/${documentId}/`, {
        institutionId,
      }),
    onSuccess: () => invalidateAdvances(qc),
  });
}
