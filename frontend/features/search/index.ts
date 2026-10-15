/**
 * Search feature barrel — public API of the module.
 *
 * Pages and tests import from here; internals stay private.
 */

export { useSearch } from "@/features/search/queries";
export type { SearchParams } from "@/features/search/queries";
export { SearchBar } from "@/features/search/SearchBar";
export { SearchResults } from "@/features/search/SearchResults";
export { SearchFilters } from "@/features/search/SearchFilters";
export { SEARCH_INDEXES, DEFAULT_SEARCH_INDEX } from "@/features/search/constants";
export type {
  SearchHit,
  SearchResults as SearchResultsModel,
  SearchIndex,
  SearchFilters as SearchFiltersModel,
} from "@/features/search/types";
