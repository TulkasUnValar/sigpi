"use client";

/**
 * Advance detail — /projects/[id]/advances/[advanceId].
 *
 * Spec (advances-ui nested list & detail):
 *   Detail MUST show review timeline + state history, plus the FSM action
 *   bar for state transitions.
 */

import Link from "next/link";
import { useParams } from "next/navigation";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { FsmActionBar } from "@/features/advances/FsmActionBar";
import { useAdvanceDetail } from "@/features/advances/queries";

export default function AdvanceDetailPage() {
  const params = useParams<{ id: string; advanceId: string }>();
  const projectId = params.id;
  const advanceId = params.advanceId;

  const detailQuery = useAdvanceDetail(advanceId);

  if (detailQuery.isLoading) {
    return (
      <AuthenticatedLayout>
        <Skeleton className="mb-4 h-8 w-64" />
        <Skeleton className="h-64" />
      </AuthenticatedLayout>
    );
  }

  const advance = detailQuery.data;
  if (!advance) {
    return (
      <AuthenticatedLayout>
        <EmptyState title="Avance no encontrado" />
      </AuthenticatedLayout>
    );
  }

  const reviews = advance.reviews ?? [];
  const stateLogs = advance.state_logs ?? [];

  return (
    <AuthenticatedLayout>
      <div className="mb-6">
        <Link
          href={`/projects/${projectId}/advances`}
          className="text-sm text-muted-foreground hover:underline"
        >
          ← Volver a avances
        </Link>
        <div className="mt-1 flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold">
            {advance.period_start} → {advance.period_end}
          </h1>
          <StatusBadge status={advance.status} />
        </div>
      </div>

      <div className="mb-6">
        <FsmActionBar advanceId={advanceId} state={advance.status} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Descripción</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Porcentaje acumulado
                </p>
                <p className="mt-1 text-lg font-semibold">
                  {advance.cumulative_percentage}%
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Período</p>
                <p className="mt-1">
                  {advance.period_start} → {advance.period_end}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Descripción</p>
                <p className="mt-1">{advance.description}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Actividades</p>
                <p className="mt-1">{advance.activities}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Dificultades
                </p>
                <p className="mt-1">{advance.difficulties || "—"}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Próximos pasos
                </p>
                <p className="mt-1">{advance.next_steps || "—"}</p>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Línea de revisión</CardTitle>
            </CardHeader>
            <CardContent>
              {reviews.length === 0 ? (
                <EmptyState title="Sin revisiones" />
              ) : (
                <ul className="space-y-2">
                  {reviews.map((r) => (
                    <li key={r.id} className="rounded-md border p-3">
                      <p>{r.review_text}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {r.review_type} · {r.created_at}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Historial de estados</CardTitle>
            </CardHeader>
            <CardContent>
              {stateLogs.length === 0 ? (
                <EmptyState title="Sin historial" />
              ) : (
                <ul className="space-y-2">
                  {stateLogs.map((log) => (
                    <li key={log.id} className="rounded-md border p-3">
                      <span className="font-medium">
                        {log.from_state} → {log.to_state}
                      </span>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {log.created_at}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </AuthenticatedLayout>
  );
}