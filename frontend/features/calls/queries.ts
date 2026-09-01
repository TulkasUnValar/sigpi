"use client";

/**
 * Calls TanStack Query hooks — list, detail, and the nested resources
 * (documents, projects, state history).
 *
 * All server data is scoped by the active institution and invalidated
 * after mutations via the calls query-key root.
 */

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { useAuthStore } from "@/store/auth";
import type {
  Call,
  CallDocument,
  CallProject,
  CallStateLog,
  Page,
} from "@/features/calls/types";

function useActiveInstitutionId(): string | null {
  return useAuthStore((s) => s.activeInstitution?.id ?? null);
}

/** List query options (filters + pagination). */
export interface CallListParams {
  page?: number;
  status?: string;
  call_type?: string;
}

/** Serialize list params into a DRF query string. */
export function buildQueryString(params: CallListParams): string {
  const sp = new URLSearchParams();
  if (params.page && params.page > 1) sp.set("page", String(params.page));
  if (params.status) sp.set("status", params.status);
  if (params.call_type) sp.set("call_type", params.call_type);
  const qs = sp.toString();
  return qs ? `?${qs}` : "";
}

/** Fetch the paginated call list with filters. */
export function useCallsList(params: CallListParams = {}) {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: queryKeys.calls.list(institutionId, params),
    queryFn: () =>
      api.get<Page<Call>>(`/api/calls/${buildQueryString(params)}`, {
        institutionId,
      }),
  });
}

/** Fetch a single call's full detail. */
export function useCallDetail(id: string) {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: queryKeys.calls.detail(institutionId, id),
    queryFn: () =>
      api.get<Call>(`/api/calls/${id}/`, { institutionId }),
  });
}

/** Fetch the metadata-only documents of a call. */
export function useCallDocuments(callId: string) {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: [...queryKeys.calls.detail(institutionId, callId), "documents"],
    queryFn: () =>
      api.get<Page<CallDocument>>(`/api/calls/${callId}/documents/`, {
        institutionId,
      }),
  });
}

/** Fetch the linked projects of a call. */
export function useCallProjects(callId: string) {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: [...queryKeys.calls.detail(institutionId, callId), "projects"],
    queryFn: () =>
      api.get<Page<CallProject>>(`/api/calls/${callId}/projects/`, {
        institutionId,
      }),
  });
}

/** Fetch the read-only state history of a call. */
export function useCallStateHistory(callId: string) {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: [...queryKeys.calls.detail(institutionId, callId), "stateHistory"],
    queryFn: () =>
      api.get<Page<CallStateLog>>(`/api/calls/${callId}/state_history/`, {
        institutionId,
      }),
  });
}