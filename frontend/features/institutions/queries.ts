"use client";

/**
 * Institutions TanStack Query hooks — root list and detail.
 *
 * The Institution is the root entity of the hierarchy: list and detail
 * load WITHOUT an active institution (scope = null) and MUST NOT send
 * the X-Institution-ID header (design decision: opt-out flag).
 *
 * fetchAllPages follows DRF `next` links — used later to assemble tree
 * levels from paginated responses.
 */

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { useAuthStore } from "@/store/auth";
import type {
  Facultad,
  Institution,
  Page,
  ResearchCenter,
  Sede,
} from "@/features/institutions/types";

export function useActiveInstitutionId(): string | null {
  return useAuthStore((s) => s.activeInstitution?.id ?? null);
}

/**
 * Consume DRF paginated responses following `next` links until null.
 * Returns the concatenated results of every page.
 */
export async function fetchAllPages<T>(
  initial: Page<T>,
  fetchPage: (url: string) => Promise<Page<T>>,
): Promise<T[]> {
  const results: T[] = [...initial.results];
  let next = initial.next;
  while (next) {
    const page = await fetchPage(next);
    results.push(...page.results);
    next = page.next;
  }
  return results;
}

/** Root institution list — institution-agnostic (RF-F02 bootstrap). */
export function useInstitutionsList() {
  return useQuery({
    queryKey: queryKeys.institutions.list(null, "institution", null),
    queryFn: () =>
      api.get<Page<Institution>>("/api/institutions/", {
        sendInstitutionId: false,
      }),
  });
}

/** Root institution detail — institution-agnostic. */
export function useInstitutionDetail(id: string) {
  return useQuery({
    queryKey: queryKeys.institutions.detail(null, "institution", id),
    queryFn: () =>
      api.get<Institution>(`/api/institutions/${id}/`, {
        sendInstitutionId: false,
      }),
    enabled: Boolean(id),
  });
}

// ──────────────────────────────────────────────────────────
// Child entity hooks (RF-F03) — Sede / Facultad / ResearchCenter
//
// Parent ids come from the URL (institution id) and optional filters
// (sede, parent_type/parent). All calls omit the X-Institution-ID header.
// `enabled` defaults to true; the tree passes isExpanded for lazy loading.
// ──────────────────────────────────────────────────────────

/**
 * Sedes of an institution — GET /api/institutions/{id}/sedes/.
 * List keys are scoped by (institution, kind, parentId).
 */
export function useSedes(institutionId: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.institutions.list(institutionId, "sede", null),
    queryFn: () =>
      api.get<Page<Sede>>(`/api/institutions/${institutionId}/sedes/`, {
        sendInstitutionId: false,
      }),
    enabled: Boolean(institutionId) && enabled,
  });
}

/**
 * Facultades of an institution — GET /api/institutions/{id}/facultades/.
 * `sedeId` optionally narrows the list (?sede=).
 */
export function useFacultades(institutionId: string, sedeId?: string, enabled = true) {
  const filter = sedeId ? `?sede=${sedeId}` : "";
  return useQuery({
    queryKey: queryKeys.institutions.list(institutionId, "facultad", sedeId ?? null),
    queryFn: () =>
      api.get<Page<Facultad>>(`/api/institutions/${institutionId}/facultades/${filter}`, {
        sendInstitutionId: false,
      }),
    enabled: Boolean(institutionId) && enabled,
  });
}

/**
 * Research centers of an institution — GET /api/institutions/{id}/centers/.
 * `parentType`/`parentId` optionally narrow the list (?parent_type=&parent=);
 * parent_type may be institution | sede | facultad (backend supports all three).
 */
export function useResearchCenters(
  institutionId: string,
  parentType?: string,
  parentId?: string | null,
  enabled = true,
) {
  const filter = parentType && parentId ? `?parent_type=${parentType}&parent=${parentId}` : "";
  return useQuery({
    queryKey: queryKeys.institutions.list(institutionId, "center", parentId ?? null),
    queryFn: () =>
      api.get<Page<ResearchCenter>>(`/api/institutions/${institutionId}/centers/${filter}`, {
        sendInstitutionId: false,
      }),
    enabled: Boolean(institutionId) && enabled,
  });
}

/** Sede detail — GET /api/sedes/{id}/. */
export function useSedeDetail(id: string) {
  return useQuery({
    queryKey: queryKeys.institutions.detail(null, "sede", id),
    queryFn: () =>
      api.get<Sede>(`/api/sedes/${id}/`, {
        sendInstitutionId: false,
      }),
    enabled: Boolean(id),
  });
}

/** Facultad detail — GET /api/facultades/{id}/. */
export function useFacultadDetail(id: string) {
  return useQuery({
    queryKey: queryKeys.institutions.detail(null, "facultad", id),
    queryFn: () =>
      api.get<Facultad>(`/api/facultades/${id}/`, {
        sendInstitutionId: false,
      }),
    enabled: Boolean(id),
  });
}

/** ResearchCenter detail — GET /api/centers/{id}/. */
export function useCenterDetail(id: string) {
  return useQuery({
    queryKey: queryKeys.institutions.detail(null, "center", id),
    queryFn: () =>
      api.get<ResearchCenter>(`/api/centers/${id}/`, {
        sendInstitutionId: false,
      }),
    enabled: Boolean(id),
  });
}
