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
  CreateAffiliationPayload,
  CreateAttachmentPayload,
  CreateExternalProfilePayload,
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

// ──────────────────────────────────────────────────────────
// Nested mutations (PR2) — affiliations, external profiles, attachments.
//
// The researcher id comes from the URL. Every call passes the active
// institutionId and invalidates `researchers.all` only on success so the
// nested lists refetch.
// ──────────────────────────────────────────────────────────

/** Create an affiliation — POST /api/researchers/{id}/affiliations/. */
export function useCreateAffiliation(id: string) {
  const qc = useQueryClient();
  const institutionId = useInstitutionId();
  return useMutation({
    mutationFn: (payload: CreateAffiliationPayload) =>
      api.post(`/api/researchers/${id}/affiliations/`, payload, { institutionId }),
    onSuccess: () => invalidateResearchers(qc),
  });
}

/** Delete an affiliation — DELETE /api/researchers/{id}/affiliations/{affId}/. */
export function useDeleteAffiliation(id: string) {
  const qc = useQueryClient();
  const institutionId = useInstitutionId();
  return useMutation({
    mutationFn: (affId: string) =>
      api.delete(`/api/researchers/${id}/affiliations/${affId}/`, { institutionId }),
    onSuccess: () => invalidateResearchers(qc),
  });
}

/** Mark an affiliation primary — POST .../affiliations/{affId}/set_primary/. */
export function useSetPrimaryAffiliation(id: string) {
  const qc = useQueryClient();
  const institutionId = useInstitutionId();
  return useMutation({
    mutationFn: (affId: string) =>
      api.post(
        `/api/researchers/${id}/affiliations/${affId}/set_primary/`,
        {},
        {
          institutionId,
        },
      ),
    onSuccess: () => invalidateResearchers(qc),
  });
}

/** Create an external profile — POST /api/researchers/{id}/profiles/. */
export function useCreateExternalProfile(id: string) {
  const qc = useQueryClient();
  const institutionId = useInstitutionId();
  return useMutation({
    mutationFn: (payload: CreateExternalProfilePayload) =>
      api.post(`/api/researchers/${id}/profiles/`, payload, { institutionId }),
    onSuccess: () => invalidateResearchers(qc),
  });
}

/** Delete an external profile — DELETE /api/researchers/{id}/profiles/{profileId}/. */
export function useDeleteExternalProfile(id: string) {
  const qc = useQueryClient();
  const institutionId = useInstitutionId();
  return useMutation({
    mutationFn: (profileId: string) =>
      api.delete(`/api/researchers/${id}/profiles/${profileId}/`, { institutionId }),
    onSuccess: () => invalidateResearchers(qc),
  });
}

/** Create an attachment (metadata only) — POST /api/researchers/{id}/attachments/. */
export function useCreateAttachment(id: string) {
  const qc = useQueryClient();
  const institutionId = useInstitutionId();
  return useMutation({
    mutationFn: (payload: CreateAttachmentPayload) =>
      api.post(`/api/researchers/${id}/attachments/`, payload, { institutionId }),
    onSuccess: () => invalidateResearchers(qc),
  });
}

/** Delete an attachment — DELETE /api/researchers/{id}/attachments/{attId}/. */
export function useDeleteAttachment(id: string) {
  const qc = useQueryClient();
  const institutionId = useInstitutionId();
  return useMutation({
    mutationFn: (attId: string) =>
      api.delete(`/api/researchers/${id}/attachments/${attId}/`, { institutionId }),
    onSuccess: () => invalidateResearchers(qc),
  });
}
