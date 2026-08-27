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
import type { Institution, Page } from "@/features/institutions/types";

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
