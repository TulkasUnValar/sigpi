"use client";

/**
 * Dashboard — role-aware home.
 *
 * Director: pending-approvals queue + KPI cards.
 * Investigator: "my projects" + average progress KPIs (approvals hidden).
 */

import { useAuthStore } from "@/store/auth";
import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { StatusBadge } from "@/components/shared/StatusBadge";
import {
  computeDirectorKpis,
  computeInvestigatorKpis,
  selectPendingApprovals,
} from "@/features/dashboard/kpi-selectors";
import {
  useProjectsList,
  useProgressList,
} from "@/features/dashboard/queries";

export default function DashboardPage() {
  const { roles } = useAuthStore();
  const isDirector = roles.includes("director") || roles.includes("admin");

  const projectsQuery = useProjectsList();
  const progressQuery = useProgressList();

  const loading = projectsQuery.isLoading || progressQuery.isLoading;
  const projects = projectsQuery.data?.results ?? [];
  const progress = progressQuery.data?.results ?? [];

  if (loading) {
    return (
      <AuthenticatedLayout>
        <div className="space-y-4">
          <Skeleton className="h-8 w-64" />
          <div className="grid gap-4 sm:grid-cols-3">
            <Skeleton className="h-28" />
            <Skeleton className="h-28" />
            <Skeleton className="h-28" />
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  const directorKpis = computeDirectorKpis(projects, progress);
  const investigatorKpis = computeInvestigatorKpis(projects, progress);
  const pending = selectPendingApprovals(projects);

  return (
    <AuthenticatedLayout>
      <h1 className="mb-6 text-2xl font-semibold">Panel de control</h1>

      <div className="grid gap-4 sm:grid-cols-3">
        {isDirector ? (
          <>
            <KpiCard title="Total de proyectos" value={directorKpis.totalProjects} />
            <KpiCard
              title="Pendientes de aprobación"
              value={directorKpis.pendingApprovals}
            />
            <KpiCard title="Avances pendientes" value={directorKpis.pendingAdvances} />
          </>
        ) : (
          <>
            <KpiCard title="Mis proyectos" value={investigatorKpis.myProjects} />
            <KpiCard
              title="Progreso promedio"
              value={`${investigatorKpis.averageProgress}%`}
            />
          </>
        )}
      </div>

      {isDirector ? (
        <section className="mt-8" aria-label="Cola de aprobaciones">
          <h2 className="mb-3 text-lg font-semibold">
            Aprobaciones pendientes
          </h2>
          {pending.length === 0 ? (
            <EmptyState
              title="Sin aprobaciones pendientes"
              description="No hay proyectos en revisión por el momento."
            />
          ) : (
            <ul className="space-y-2">
              {pending.map((p) => (
                <li
                  key={p.id}
                  className="flex items-center justify-between rounded-md border p-3"
                >
                  <span className="font-medium">{p.title}</span>
                  <StatusBadge status={p.status} />
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}
    </AuthenticatedLayout>
  );
}

function KpiCard({ title, value }: { title: string; value: string | number }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-bold">{value}</p>
      </CardContent>
    </Card>
  );
}