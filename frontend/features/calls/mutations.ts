"use client";

/**
 * Calls mutations — create, update, delete, and the 5 FSM transitions.
 *
 * Spec (calls-ui server state):
 *   - Every successful call mutation invalidates the calls root so list,
 *     detail and nested keys refetch.
 *   - On failure the cache is NOT invalidated and the error is surfaced
 *     by the caller (403/409 details via getErrorMessage/Toaster).
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useActiveInstitutionId } from "@/features/calls/queries";
import type { Call, CallDocument, CallProject, CreateCallPayload } from "@/features/calls/types";

/** Invalidate every query derived from the calls resource. */
function invalidateCalls(qc: ReturnType<typeof useQueryClient>) {
  void qc.invalidateQueries({ queryKey: ["calls"] });
}

/** Create a call and invalidate the calls cache. */
export function useCreateCall() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateCallPayload) => api.post<Call>("/api/calls/", payload),
    onSuccess: () => invalidateCalls(qc),
  });
}

/** Update a call (PATCH) and invalidate the calls cache. */
export function useUpdateCall() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: { id: string } & CreateCallPayload) =>
      api.patch<Call>(`/api/calls/${id}/`, payload),
    onSuccess: () => invalidateCalls(qc),
  });
}

/** Delete a call and invalidate the calls cache. */
export function useDeleteCall() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/api/calls/${id}/`),
    onSuccess: () => invalidateCalls(qc),
  });
}

/**
 * Trigger a call FSM transition. `action` is the DRF endpoint action
 * (open_call | close_call | start_evaluation | publish_results | archive).
 */
export function useCallTransition() {
  const qc = useQueryClient();
  const institutionId = useActiveInstitutionId();
  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) =>
      api.post<Call>(`/api/calls/${id}/${action}/`, {}, { institutionId }),
    onSuccess: () => invalidateCalls(qc),
  });
}

// ── Nested documents ─────────────────────────────────────

/** Metadata-only document payload (CallDocumentSerializer writable fields). */
export interface DocumentPayload {
  name: string;
  doc_type: string;
  external_url: string;
}

/** Create a document under a call and invalidate the calls cache. */
export function useCreateDocument() {
  const qc = useQueryClient();
  const institutionId = useActiveInstitutionId();
  return useMutation({
    mutationFn: ({ callId, ...payload }: { callId: string } & DocumentPayload) =>
      api.post<CallDocument>(`/api/calls/${callId}/documents/`, payload, {
        institutionId,
      }),
    onSuccess: () => invalidateCalls(qc),
  });
}

/** Update a document's metadata and invalidate the calls cache. */
export function useUpdateDocument() {
  const qc = useQueryClient();
  const institutionId = useActiveInstitutionId();
  return useMutation({
    mutationFn: ({
      callId,
      documentId,
      ...payload
    }: { callId: string; documentId: string } & DocumentPayload) =>
      api.patch<CallDocument>(`/api/calls/${callId}/documents/${documentId}/`, payload, {
        institutionId,
      }),
    onSuccess: () => invalidateCalls(qc),
  });
}

/** Delete a document and invalidate the calls cache. */
export function useDeleteDocument() {
  const qc = useQueryClient();
  const institutionId = useActiveInstitutionId();
  return useMutation({
    mutationFn: ({ callId, documentId }: { callId: string; documentId: string }) =>
      api.delete<void>(`/api/calls/${callId}/documents/${documentId}/`, {
        institutionId,
      }),
    onSuccess: () => invalidateCalls(qc),
  });
}

// ── Nested project links ─────────────────────────────────

/** Link a project to an `abierta` call and invalidate the calls cache. */
export function useLinkProject() {
  const qc = useQueryClient();
  const institutionId = useActiveInstitutionId();
  return useMutation({
    mutationFn: ({ callId, project }: { callId: string; project: string }) =>
      api.post<CallProject>(
        `/api/calls/${callId}/projects/`,
        { project },
        {
          institutionId,
        },
      ),
    onSuccess: () => invalidateCalls(qc),
  });
}

/** Unlink a project from a call and invalidate the calls cache. */
export function useUnlinkProject() {
  const qc = useQueryClient();
  const institutionId = useActiveInstitutionId();
  return useMutation({
    mutationFn: ({ callId, projectId }: { callId: string; projectId: string }) =>
      api.delete<void>(`/api/calls/${callId}/projects/${projectId}/`, {
        institutionId,
      }),
    onSuccess: () => invalidateCalls(qc),
  });
}
