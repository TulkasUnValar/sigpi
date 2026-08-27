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
  CreateCenterPayload,
  CreateFacultadPayload,
  CreateInstitutionPayload,
  CreateResearchGroupPayload,
  CreateResearchLinePayload,
  CreateSedePayload,
  Facultad,
  Institution,
  ResearchCenter,
  ResearchGroup,
  ResearchLine,
  Sede,
  UpdateCenterPayload,
  UpdateFacultadPayload,
  UpdateInstitutionPayload,
  UpdateResearchGroupPayload,
  UpdateResearchLinePayload,
  UpdateSedePayload,
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

// ──────────────────────────────────────────────────────────
// Child entity mutations (RF-F03) — Sede / Facultad / ResearchCenter
//
// The parent (institution) id comes from the URL; it is NEVER sent in the
// body. Optional references (sede/facultad) ARE body fields. Every call
// omits the X-Institution-ID header and invalidates `institutions.all`
// only on success.
// ──────────────────────────────────────────────────────────

// ── Sede ──────────────────────────────────────────────────

/** Create a sede under an institution — POST /api/institutions/{pk}/sedes/. */
export function useCreateSede(institutionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateSedePayload) =>
      api.post<Sede>(`/api/institutions/${institutionId}/sedes/`, payload, {
        sendInstitutionId: false,
      }),
    onSuccess: () => invalidateInstitutions(qc),
  });
}

/** Update a sede — PATCH /api/sedes/{id}/. */
export function useUpdateSede() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UpdateSedePayload }) =>
      api.patch<Sede>(`/api/sedes/${id}/`, payload, {
        sendInstitutionId: false,
      }),
    onSuccess: () => invalidateInstitutions(qc),
  });
}

/** Delete a sede — DELETE /api/sedes/{id}/. */
export function useDeleteSede() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete<void>(`/api/sedes/${id}/`, {
        sendInstitutionId: false,
      }),
    onSuccess: () => invalidateInstitutions(qc),
  });
}

/** Sede FSM transition — POST /api/sedes/{id}/{action}/. */
export function useSedeTransition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) =>
      api.post<Sede>(
        `/api/sedes/${id}/${action}/`,
        {},
        {
          sendInstitutionId: false,
        },
      ),
    onSuccess: () => invalidateInstitutions(qc),
  });
}

// ── Facultad ──────────────────────────────────────────────

/** Create a facultad under an institution — POST /api/institutions/{pk}/facultades/. */
export function useCreateFacultad(institutionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateFacultadPayload) =>
      api.post<Facultad>(`/api/institutions/${institutionId}/facultades/`, payload, {
        sendInstitutionId: false,
      }),
    onSuccess: () => invalidateInstitutions(qc),
  });
}

/** Update a facultad — PATCH /api/facultades/{id}/. */
export function useUpdateFacultad() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UpdateFacultadPayload }) =>
      api.patch<Facultad>(`/api/facultades/${id}/`, payload, {
        sendInstitutionId: false,
      }),
    onSuccess: () => invalidateInstitutions(qc),
  });
}

/** Delete a facultad — DELETE /api/facultades/{id}/. */
export function useDeleteFacultad() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete<void>(`/api/facultades/${id}/`, {
        sendInstitutionId: false,
      }),
    onSuccess: () => invalidateInstitutions(qc),
  });
}

/** Facultad FSM transition — POST /api/facultades/{id}/{action}/. */
export function useFacultadTransition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) =>
      api.post<Facultad>(
        `/api/facultades/${id}/${action}/`,
        {},
        {
          sendInstitutionId: false,
        },
      ),
    onSuccess: () => invalidateInstitutions(qc),
  });
}

// ── ResearchCenter ────────────────────────────────────────

/** Create a center under an institution — POST /api/institutions/{pk}/centers/. */
export function useCreateCenter(institutionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateCenterPayload) =>
      api.post<ResearchCenter>(`/api/institutions/${institutionId}/centers/`, payload, {
        sendInstitutionId: false,
      }),
    onSuccess: () => invalidateInstitutions(qc),
  });
}

/** Update a center — PATCH /api/centers/{id}/. */
export function useUpdateCenter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UpdateCenterPayload }) =>
      api.patch<ResearchCenter>(`/api/centers/${id}/`, payload, {
        sendInstitutionId: false,
      }),
    onSuccess: () => invalidateInstitutions(qc),
  });
}

/** Delete a center — DELETE /api/centers/{id}/. */
export function useDeleteCenter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete<void>(`/api/centers/${id}/`, {
        sendInstitutionId: false,
      }),
    onSuccess: () => invalidateInstitutions(qc),
  });
}

/** Center FSM transition — POST /api/centers/{id}/{action}/. */
export function useCenterTransition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) =>
      api.post<ResearchCenter>(
        `/api/centers/${id}/${action}/`,
        {},
        {
          sendInstitutionId: false,
        },
      ),
    onSuccess: () => invalidateInstitutions(qc),
  });
}

// ──────────────────────────────────────────────────────────
// Leaf entity mutations (RF-F03) — ResearchGroup / ResearchLine
//
// Parent ids (center for groups, group for lines) come from the URL and
// are NEVER sent in the body. Every call omits the X-Institution-ID
// header and invalidates `institutions.all` only on success.
// ──────────────────────────────────────────────────────────

// ── ResearchGroup ─────────────────────────────────────────

/** Create a group under a center — POST /api/centers/{pk}/groups/. */
export function useCreateResearchGroup(centerId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateResearchGroupPayload) =>
      api.post<ResearchGroup>(`/api/centers/${centerId}/groups/`, payload, {
        sendInstitutionId: false,
      }),
    onSuccess: () => invalidateInstitutions(qc),
  });
}

/** Update a group — PATCH /api/groups/{id}/. */
export function useUpdateResearchGroup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UpdateResearchGroupPayload }) =>
      api.patch<ResearchGroup>(`/api/groups/${id}/`, payload, {
        sendInstitutionId: false,
      }),
    onSuccess: () => invalidateInstitutions(qc),
  });
}

/** Delete a group — DELETE /api/groups/{id}/. */
export function useDeleteResearchGroup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete<void>(`/api/groups/${id}/`, {
        sendInstitutionId: false,
      }),
    onSuccess: () => invalidateInstitutions(qc),
  });
}

/** Group FSM transition — POST /api/groups/{id}/{action}/. */
export function useResearchGroupTransition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) =>
      api.post<ResearchGroup>(
        `/api/groups/${id}/${action}/`,
        {},
        {
          sendInstitutionId: false,
        },
      ),
    onSuccess: () => invalidateInstitutions(qc),
  });
}

// ── ResearchLine ──────────────────────────────────────────

/** Create a line under a group — POST /api/groups/{pk}/lines/. */
export function useCreateResearchLine(groupId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateResearchLinePayload) =>
      api.post<ResearchLine>(`/api/groups/${groupId}/lines/`, payload, {
        sendInstitutionId: false,
      }),
    onSuccess: () => invalidateInstitutions(qc),
  });
}

/** Update a line — PATCH /api/lines/{id}/. */
export function useUpdateResearchLine() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UpdateResearchLinePayload }) =>
      api.patch<ResearchLine>(`/api/lines/${id}/`, payload, {
        sendInstitutionId: false,
      }),
    onSuccess: () => invalidateInstitutions(qc),
  });
}

/** Delete a line — DELETE /api/lines/{id}/. */
export function useDeleteResearchLine() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete<void>(`/api/lines/${id}/`, {
        sendInstitutionId: false,
      }),
    onSuccess: () => invalidateInstitutions(qc),
  });
}

/** Line FSM transition — POST /api/lines/{id}/{action}/. */
export function useResearchLineTransition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) =>
      api.post<ResearchLine>(
        `/api/lines/${id}/${action}/`,
        {},
        {
          sendInstitutionId: false,
        },
      ),
    onSuccess: () => invalidateInstitutions(qc),
  });
}
