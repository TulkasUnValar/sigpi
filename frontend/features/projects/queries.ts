"use client";

/**
 * Projects TanStack Query hooks — list, detail, observations, state
 * history, and the hierarchy/researcher options used by the wizard.
 *
 * All server data is scoped by the active institution and invalidated
 * after FSM mutations.
 */

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { useAuthStore } from "@/store/auth";
import type {
  HierarchyNode,
  Page,
  ProjectDetail,
  ProjectList,
  ProjectObservation,
  ProjectStateLog,
  ResearcherOption,
} from "@/features/projects/types";

export function useActiveInstitutionId(): string | null {
  return useAuthStore((s) => s.activeInstitution?.id ?? null);
}

/** List query options (filters + pagination). */
export interface ProjectListParams {
  page?: number;
  status?: string;
  center?: string;
  line?: string;
  year?: string;
  search?: string;
  [key: string]: unknown;
}

function buildQueryString(params: ProjectListParams): string {
  const sp = new URLSearchParams();
  if (params.page && params.page > 1) sp.set("page", String(params.page));
  if (params.status) sp.set("status", params.status);
  if (params.center) sp.set("center", params.center);
  if (params.year) sp.set("start_date_after", `${params.year}-01-01`);
  if (params.search) sp.set("search", params.search);
  const qs = sp.toString();
  return qs ? `?${qs}` : "";
}

/** Fetch the paginated project list with filters. */
export function useProjectsList(params: ProjectListParams = {}) {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: queryKeys.projects.list(institutionId, params),
    queryFn: () =>
      api.get<Page<ProjectList>>(
        `/api/projects/${buildQueryString(params)}`,
        { institutionId },
      ),
  });
}

/** Fetch a single project's full detail (with nested members/documents). */
export function useProjectDetail(id: string) {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: queryKeys.projects.detail(institutionId, id),
    queryFn: () =>
      api.get<ProjectDetail>(`/api/projects/${id}/`, { institutionId }),
  });
}

/** Fetch observations for a project (append-only log). */
export function useProjectObservations(id: string) {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: [...queryKeys.projects.detail(institutionId, id), "observations"],
    queryFn: () =>
      api.get<Page<ProjectObservation>>(`/api/projects/${id}/observations/`, {
        institutionId,
      }),
  });
}

/** Fetch state history for a project. */
export function useProjectStateHistory(id: string) {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: [...queryKeys.projects.detail(institutionId, id), "history"],
    queryFn: () =>
      api.get<Page<ProjectStateLog>>(`/api/projects/${id}/state_history/`, {
        institutionId,
      }),
  });
}

/** Fetch research centers for the active institution (wizard). */
export function useCenters() {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: [...queryKeys.projects.all, "centers", institutionId],
    queryFn: () =>
      api.get<HierarchyNode[]>(`/api/institutions/${institutionId}/centers/`, {
        institutionId,
      }),
  });
}

/** Fetch groups for a selected center (dependent select). */
export function useGroups(centerId: string | null) {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: [...queryKeys.projects.all, "groups", institutionId, centerId],
    queryFn: () =>
      api.get<HierarchyNode[]>(`/api/centers/${centerId}/groups/`, {
        institutionId,
      }),
    enabled: Boolean(centerId),
  });
}

/** Fetch lines for a selected group (dependent select). */
export function useLines(groupId: string | null) {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: [...queryKeys.projects.all, "lines", institutionId, groupId],
    queryFn: () =>
      api.get<HierarchyNode[]>(`/api/groups/${groupId}/lines/`, {
        institutionId,
      }),
    enabled: Boolean(groupId),
  });
}

/** Fetch researchers for PI/team selects (wizard). */
export function useResearchers() {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: [...queryKeys.projects.all, "researchers", institutionId],
    queryFn: () =>
      api.get<ResearcherOption[]>(`/api/researchers/`, { institutionId }),
  });
}
