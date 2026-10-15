"use client";

/**
 * SearchResults — renders paginated search hits with highlighting.
 *
 * Each hit displays title/name and description with Meilisearch
 * highlighting (rendered via dangerouslySetInnerHTML — safe HTML).
 * Links to the entity detail page via SEARCH_INDEXES routes.
 */

import Link from "next/link";
import { ChevronLeft, ChevronRight, FileText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SEARCH_INDEXES } from "./constants";
import type { SearchHit, SearchResults as SearchResultsModel } from "./types";

export interface SearchResultsProps {
  results: SearchResultsModel | undefined;
  offset: number;
  limit: number;
  onPageChange: (offset: number) => void;
}

/**
 * Render highlighted field if available, otherwise plain text.
 * Meilisearch wraps matches in <mark> tags (safe HTML).
 */
function HighlightedText({
  hit,
  field,
  fallback,
}: {
  hit: SearchHit;
  field: keyof SearchHit;
  fallback?: string;
}) {
  const formatted = hit._formatted?.[field as string];
  const plain = (hit[field] as string) || fallback || "";

  if (formatted) {
    return <span dangerouslySetInnerHTML={{ __html: formatted }} />;
  }
  return <>{plain}</>;
}

/**
 * Infer the search index from the hit's _formatted keys or fall back
 * to the first SEARCH_INDEXES entry (projects).
 */
function getHitRoute(hit: SearchHit): string {
  // Prefer explicit index hint if present.
  const indexHint = hit._index as string | undefined;
  if (indexHint) {
    const meta = SEARCH_INDEXES.find((si) => si.value === indexHint);
    if (meta) return `${meta.route}/${hit.id}`;
  }
  // Fallback: projects (most common).
  return `/projects/${hit.id}`;
}

export function SearchResults({ results, offset, limit, onPageChange }: SearchResultsProps) {
  if (!results) return null;

  const { hits, estimatedTotalHits, query } = results;
  const hasResults = hits.length > 0;
  const hasMore = offset + limit < estimatedTotalHits;
  const canGoPrev = offset > 0;

  return (
    <div className="space-y-4" data-testid="search-results">
      {/* Results header */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {hasResults ? (
            <>
              <span className="font-medium text-foreground">{estimatedTotalHits}</span>{" "}
              {estimatedTotalHits === 1 ? "resultado" : "resultados"} para{" "}
              <span className="font-medium text-foreground">&ldquo;{query}&rdquo;</span>
            </>
          ) : (
            <>No se encontraron resultados para &ldquo;{query}&rdquo;</>
          )}
        </p>
      </div>

      {/* Results list */}
      {hasResults ? (
        <div className="space-y-3">
          {hits.map((hit) => (
            <Link key={hit.id} href={getHitRoute(hit)} data-testid="search-hit">
              <Card className="transition-colors hover:border-primary">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">
                    <HighlightedText hit={hit} field="title" fallback={hit.name} />
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {(hit.description || hit._formatted?.description) && (
                    <p className="text-sm text-muted-foreground line-clamp-3">
                      <HighlightedText hit={hit} field="description" />
                    </p>
                  )}
                  {hit._index && (
                    <Badge variant="secondary" className="mt-2 text-xs">
                      {SEARCH_INDEXES.find((si) => si.value === hit._index)?.label || hit._index}
                    </Badge>
                  )}
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-12">
            <FileText className="h-12 w-12 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Intenta con otros términos o ajusta los filtros.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Pagination */}
      {hasResults && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={!canGoPrev}
            onClick={() => onPageChange(Math.max(0, offset - limit))}
            data-testid="search-prev"
          >
            <ChevronLeft className="h-4 w-4" />
            Anterior
          </Button>
          <span className="text-sm text-muted-foreground">
            {offset + 1}–{Math.min(offset + limit, estimatedTotalHits)} de {estimatedTotalHits}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={!hasMore}
            onClick={() => onPageChange(offset + limit)}
            data-testid="search-next"
          >
            Siguiente
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
