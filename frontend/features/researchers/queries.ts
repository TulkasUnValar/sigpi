"use client";

/**
 * Researchers TanStack Query hooks — list, detail, and nested child lists.
 *
 * Spec (researchers-ui): the module is institution-scoped and read-first.
 * All hooks pass the active institutionId to `api` so the X-Institution-ID
 * header is sent. The list consumes Page<ResearcherList> (25/page).
 */

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { useAuthStore } from "@/store/auth";
import type {
  ExternalProfile,
  Page,
  Researcher,
  ResearcherAffiliation,
  ResearcherAttachment,
  ResearcherList,
} from "@/features/researchers/types";

export function useActiveInstitutionId(): string | null {
  return useAuthStore((s) => s.activeInstitution?.id ?? null);
}

/** List query params (pagination). */
export interface ResearchersListParams {
  page?: number;
}

/**
 * Fetch the paginated researcher list for the active institution.
 * Defaults to page 1 (25/page on the backend). Passes institutionId so
 * the tenant header is sent.
 */
export function useResearchersList(params: ResearchersListParams = {}) {
  const institutionId = useActiveInstitutionId();
  const page = params.page ?? 1;
  const qs = page > 1 ? `?page=${page}` : "";
  return useQuery({
    queryKey: queryKeys.researchers.list(institutionId, page),
    queryFn: () => api.get<Page<ResearcherList>>(`/api/researchers/${qs}`, { institutionId }),
  });
}

/** Fetch a single researcher's full detail. */
export function useResearcherDetail(id: string) {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: queryKeys.researchers.detail(institutionId, id),
    queryFn: () => api.get<Researcher>(`/api/researchers/${id}/`, { institutionId }),
    enabled: Boolean(id),
  });
}

/** Fetch affiliations for a researcher (nested list). */
export function useResearcherAffiliations(id: string) {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: queryKeys.researchers.affiliations(institutionId, id),
    queryFn: () =>
      api.get<Page<ResearcherAffiliation>>(`/api/researchers/${id}/affiliations/`, {
        institutionId,
      }),
    enabled: Boolean(id),
  });
}

/** Fetch external profiles for a researcher (nested list). */
export function useResearcherProfiles(id: string) {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: queryKeys.researchers.profiles(institutionId, id),
    queryFn: () =>
      api.get<Page<ExternalProfile>>(`/api/researchers/${id}/profiles/`, {
        institutionId,
      }),
    enabled: Boolean(id),
  });
}

/** Fetch attachments for a researcher (nested list). */
export function useResearcherAttachments(id: string) {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: queryKeys.researchers.attachments(institutionId, id),
    queryFn: () =>
      api.get<Page<ResearcherAttachment>>(`/api/researchers/${id}/attachments/`, {
        institutionId,
      }),
    enabled: Boolean(id),
  });
}
