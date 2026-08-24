"use client";

/**
 * Advances nested list — /projects/[id]/advances.
 *
 * Spec (advances-ui nested list & detail):
 *   GIVEN a project with advances
 *   WHEN visiting /projects/{id}/advances
 *   THEN list + cumulative % render.
 *
 * Shows each advance (period, status, cumulative %) plus a project-level
 * cumulative-progress indicator (average of the advances' percentages).
 */

import Link from "next/link";
import { useParams } from "next/navigation";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { useAdvancesList } from "@/features/advances/queries";

/** Average cumulative percentage across the project's advances. */
export function computeCumulativeAverage(percentages: number[]): number {
  if (percentages.length === 0) return 0;
  const total = percentages.reduce((sum, p) => sum + p, 0);
  return Math.round(total / percentages.length);
}

export default function AdvancesPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;

  const advancesQuery = useAdvancesList(projectId);
  const advances = advancesQuery.data?.results ?? [];

  const average = computeCumulativeAverage(
    advances.map((a) => a.cumulative_percentage),
  );

  return (
    <AuthenticatedLayout>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <Link
            href={`/projects/${projectId}`}
            className="text-sm text-muted-foreground hover:underline"
          >
            ← Volver al proyecto
          </Link>
          <h1 className="mt-1 text-2xl font-semibold">Avances</h1>
        </div>
        <Button asChild>
          <Link href={`/projects/${projectId}/advances/new`}>Nuevo avance</Link>
        </Button>
      </div>

      {/* Cumulative progress indicator */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-base">Progreso acumulado del proyecto</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            <div
              role="progressbar"
              aria-valuenow={average}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Progreso acumulado"
              className="h-2 flex-1 overflow-hidden rounded-full bg-muted"
            >
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${average}%` }}
              />
            </div>
            <span className="text-sm font-medium tabular-nums">{average}%</span>
          </div>
        </CardContent>
      </Card>

      {advancesQuery.isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-14" />
          ))}
        </div>
      ) : advances.length === 0 ? (
        <EmptyState
          title="No hay avances"
          description="Registra el primer avance del proyecto para comenzar."
        />
      ) : (
        <ul className="space-y-2">
          {advances.map((a) => (
            <li key={a.id}>
              <Link
                href={`/projects/${projectId}/advances/${a.id}`}
                className="block rounded-lg border p-4 transition-colors hover:bg-accent/50"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="font-medium">
                      {a.period_start} → {a.period_end}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {a.id}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusBadge status={a.status} />
                    <span className="text-sm font-medium tabular-nums">
                      {a.cumulative_percentage}%
                    </span>
                  </div>
                </div>
                <div
                  role="progressbar"
                  aria-valuenow={a.cumulative_percentage}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label={`Progreso del avance ${a.id}`}
                  className="mt-3 h-1.5 overflow-hidden rounded-full bg-muted"
                >
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${a.cumulative_percentage}%` }}
                  />
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </AuthenticatedLayout>
  );
}