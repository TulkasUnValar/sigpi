"use client";

/**
 * ResearcherList — paginated researchers table.
 *
 * Spec (researchers-ui list): renders the paginated list with a
 * completeness bar per row, an active/inactive StatusBadge, row actions
 * (detail + edit), and DRF-driven pagination controls. Empty state with
 * a create CTA is handled by the page composition layer; this component
 * shows a plain empty message when no rows exist.
 */

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { CompletenessBar } from "@/features/researchers/CompletenessBar";
import type { ResearcherList as ResearcherListRow } from "@/features/researchers/types";

interface ResearcherListProps {
  researchers: ResearcherListRow[];
  loading?: boolean;
  page: number;
  count: number;
  hasNext: boolean;
  hasPrevious: boolean;
  onPageChange: (page: number) => void;
}

/** Derive the StatusBadge status value from the researcher is_active flag. */
export function researcherStatus(isActive: boolean): string {
  return isActive ? "active" : "inactive";
}

export function ResearcherList({
  researchers,
  loading,
  page,
  count,
  hasNext,
  hasPrevious,
  onPageChange,
}: ResearcherListProps) {
  return (
    <div>
      {researchers.length === 0 ? (
        <p className="py-10 text-center text-sm text-muted-foreground">No hay investigadores</p>
      ) : (
        <div className="overflow-hidden rounded-lg border">
          <table aria-label="Lista de investigadores" className="w-full text-sm">
            <thead className="border-b bg-muted/50 text-left">
              <tr>
                <th scope="col" className="px-4 py-3 font-medium">
                  Nombre
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Estado
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Completitud
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody>
              {researchers.map((r) => (
                <tr key={r.id} className="border-b last:border-0">
                  <td className="px-4 py-3">
                    <Link href={`/researchers/${r.id}`} className="font-medium hover:underline">
                      {r.full_name}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={researcherStatus(r.is_active)} />
                  </td>
                  <td className="px-4 py-3">
                    <CompletenessBar score={r.completeness_score} className="max-w-40" />
                  </td>
                  <td className="px-4 py-3">
                    <Button asChild variant="outline" size="sm">
                      <Link href={`/researchers/${r.id}/edit`}>Editar</Link>
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-4 flex items-center justify-between">
        <Button
          variant="outline"
          size="sm"
          disabled={!hasPrevious || loading}
          onClick={() => onPageChange(page - 1)}
        >
          Anterior
        </Button>
        <span aria-live="polite" className="text-sm text-muted-foreground">
          Página {page} · {count} investigadores
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={!hasNext || loading}
          onClick={() => onPageChange(page + 1)}
        >
          Siguiente
        </Button>
      </div>
    </div>
  );
}
