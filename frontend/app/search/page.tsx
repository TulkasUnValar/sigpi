"use client";

/**
 * Search page — thin adapter over AuthenticatedLayout.
 *
 * Composes SearchBar, SearchFilters, and SearchResults.
 * Manages search state (query, index, filters, pagination).
 */

import { Suspense, useState } from "react";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuthStore } from "@/store/auth";
import { DEFAULT_SEARCH_INDEX } from "@/features/search/constants";
import { SearchBar } from "@/features/search/SearchBar";
import { SearchFilters } from "@/features/search/SearchFilters";
import { SearchResults } from "@/features/search/SearchResults";
import { useSearch } from "@/features/search/queries";
import type { SearchFilters as SearchFiltersModel, SearchIndex } from "@/features/search/types";

const DEFAULT_LIMIT = 25;

function SearchPageContent() {
  const { roles } = useAuthStore();
  const isSuperadmin = roles.includes("superadmin") || roles.includes("admin");

  const [query, setQuery] = useState("");
  const [index, setIndex] = useState<SearchIndex | "all">(DEFAULT_SEARCH_INDEX);
  const [filters, setFilters] = useState<SearchFiltersModel>({});
  const [offset, setOffset] = useState(0);

  const { data, isLoading } = useSearch({
    query,
    index,
    filters,
    offset,
    limit: DEFAULT_LIMIT,
  });

  const handleQueryChange = (value: string) => {
    setQuery(value);
    setOffset(0); // Reset pagination on new search
  };

  const handleIndexChange = (value: SearchIndex | "all") => {
    setIndex(value);
    setOffset(0);
  };

  const handleFilterChange = (newFilters: SearchFiltersModel) => {
    setFilters(newFilters);
    setOffset(0);
  };

  const handlePageChange = (newOffset: number) => {
    setOffset(newOffset);
    // Scroll to top on page change
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Búsqueda</h1>
        <p className="mt-1 text-muted-foreground">
          Busca en proyectos, investigadores, productos, convocatorias y avances.
        </p>
      </div>

      {/* Search bar */}
      <SearchBar
        query={query}
        index={index}
        isLoading={isLoading}
        onQueryChange={handleQueryChange}
        onIndexChange={handleIndexChange}
      />

      {/* Filters */}
      <SearchFilters
        filters={filters}
        isSuperadmin={isSuperadmin}
        onFilterChange={handleFilterChange}
      />

      {/* Results */}
      {isLoading ? (
        <div className="space-y-3" data-testid="search-loading">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="space-y-2 rounded-md border p-4">
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-2/3" />
            </div>
          ))}
        </div>
      ) : query.length >= 2 ? (
        <SearchResults
          results={data}
          offset={offset}
          limit={DEFAULT_LIMIT}
          onPageChange={handlePageChange}
        />
      ) : query.length > 0 ? (
        <p className="text-center text-sm text-muted-foreground">
          Ingresa al menos 2 caracteres para buscar.
        </p>
      ) : null}
    </div>
  );
}

export default function SearchPage() {
  return (
    <AuthenticatedLayout>
      <Suspense
        fallback={
          <div className="mx-auto max-w-5xl space-y-6">
            <div className="space-y-2">
              <Skeleton className="h-8 w-48" />
              <Skeleton className="h-4 w-96" />
            </div>
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        }
      >
        <SearchPageContent />
      </Suspense>
    </AuthenticatedLayout>
  );
}
