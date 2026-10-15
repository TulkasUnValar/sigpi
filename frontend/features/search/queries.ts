"use client";

/**
 * Search TanStack Query hooks — full-text search with filters.
 *
 * useSearch() wraps GET /api/search/ with Meilisearch response shape.
 * Enabled only when query length >= 2 (avoid noise on single chars).
 * Scoped by active institution via X-Institution-ID header.
 */

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { useActiveInstitutionId } from "@/features/projects/queries";
import type { SearchFilters, SearchResults, SearchIndex } from "./types";

/** Parameters for the search query hook. */
export interface SearchParams {
  query: string;
  index?: SearchIndex | "all";
  filters?: SearchFilters;
  offset?: number;
  limit?: number;
}

/**
 * Fetch search results from Meilisearch via the backend.
 *
 * Enabled only when query.length >= 2. Filters are JSON-encoded
 * for the backend query param.
 */
export function useSearch({
  query,
  index = "all",
  filters = {},
  offset = 0,
  limit = 25,
}: SearchParams) {
  const institutionId = useActiveInstitutionId();

  return useQuery({
    queryKey: queryKeys.search.list(institutionId, query, index, filters),
    queryFn: () => {
      const sp = new URLSearchParams();
      sp.set("q", query);
      if (index !== "all") sp.set("index", index);
      if (Object.keys(filters).length > 0) {
        sp.set("filters", JSON.stringify(filters));
      }
      if (offset > 0) sp.set("offset", String(offset));
      if (limit !== 25) sp.set("limit", String(limit));

      const qs = sp.toString();
      return api.get<SearchResults>(`/api/search/${qs ? `?${qs}` : ""}`, {
        institutionId,
      });
    },
    enabled: query.length >= 2,
  });
}
