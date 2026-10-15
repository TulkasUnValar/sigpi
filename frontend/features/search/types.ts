/**
 * Search feature types — mirror the Meilisearch response shape.
 *
 * - SearchHit: individual result with optional highlighted fields.
 * - SearchResults: paginated search response from Meilisearch.
 * - SearchIndex: available search indices (projects, researchers, etc).
 * - SearchFilters: filter options for narrowing search scope.
 */

/** Individual search hit with optional Meilisearch highlighting. */
export interface SearchHit {
  id: string;
  title?: string;
  name?: string;
  description?: string;
  _formatted?: Record<string, string>;
  [key: string]: unknown;
}

/** Meilisearch search response envelope. */
export interface SearchResults {
  hits: SearchHit[];
  query: string;
  processingTimeMs: number;
  estimatedTotalHits: number;
  offset: number;
  limit: number;
}

/** Available search indices (each maps to a Meilisearch index). */
export type SearchIndex = "projects" | "researchers" | "products" | "calls" | "advances";

/** Filter options for narrowing search scope. */
export interface SearchFilters {
  institution?: string;
  center?: string;
  line?: string;
  status?: string;
  year?: string;
  type?: string;
}
