"use client";

/**
 * Dashboard — role-aware home with server-side KPIs and charts.
 *
 * Director/admin: all KPIs and charts.
 * Researcher: limited view (backend scopes data to own projects).
 * Auditor: read-only access (same as director).
 *
 * Uses /api/dashboard/summary/ endpoint for pre-computed indicators and charts.
 */

import { useAuthStore } from "@/store/auth";
import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { useDashboardSummary } from "@/features/dashboard/queries";
import { ProjectsByStatusChart } from "@/features/dashboard/charts/ProjectsByStatusChart";
import { ProjectsByCenterChart } from "@/features/dashboard/charts/ProjectsByCenterChart";
import { BudgetExecutionChart } from "@/features/dashboard/charts/BudgetExecutionChart";
import { ProgressReportsChart } from "@/features/dashboard/charts/ProgressReportsChart";

export default function DashboardPage() {
  const { roles } = useAuthStore();
  const isDirector =
    roles.includes("director") || roles.includes("admin") || roles.includes("auditor");

  const { data, isLoading, error } = useDashboardSummary();

  if (isLoading) {
    return (
      <AuthenticatedLayout>
        <div className="space-y-4">
          <Skeleton className="h-8 w-64" />
          <div className="grid gap-4 sm:grid-cols-3">
            <Skeleton className="h-28" />
            <Skeleton className="h-28" />
            <Skeleton className="h-28" />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <Skeleton className="h-80" />
            <Skeleton className="h-80" />
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  if (error || !data) {
    return (
      <AuthenticatedLayout>
        <EmptyState
          title="Error al cargar el dashboard"
          description="No se pudieron cargar los datos del dashboard. Intenta recargar la página."
        />
      </AuthenticatedLayout>
    );
  }

  const { indicators, charts } = data;

  return (
    <AuthenticatedLayout>
      <h1 className="mb-6 text-2xl font-semibold">Panel de control</h1>

      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {isDirector ? (
          <>
            <KpiCard title="Total de proyectos" value={indicators["IND-001"]} />
            <KpiCard title="Pendientes de aprobación" value={indicators["IND-004"]} />
            <KpiCard title="Avances pendientes" value={indicators["IND-005"]} />
            <KpiCard title="Progreso promedio" value={`${indicators["IND-006"].toFixed(1)}%`} />
            <KpiCard title="Proyectos completos" value={indicators["IND-013"]} />
          </>
        ) : (
          <>
            <KpiCard title="Mis proyectos" value={indicators["IND-001"]} />
            <KpiCard title="Progreso promedio" value={`${indicators["IND-006"].toFixed(1)}%`} />
          </>
        )}
      </div>

      {/* Charts */}
      <section className="mt-8 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Proyectos por estado</CardTitle>
          </CardHeader>
          <CardContent>
            <ProjectsByStatusChart data={charts.projects_by_status} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Proyectos por centro</CardTitle>
          </CardHeader>
          <CardContent>
            <ProjectsByCenterChart data={charts.projects_by_center} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Ejecución presupuestal</CardTitle>
          </CardHeader>
          <CardContent>
            <BudgetExecutionChart data={charts.budget} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Informes de avance</CardTitle>
          </CardHeader>
          <CardContent>
            <ProgressReportsChart data={charts.progress_reports} />
          </CardContent>
        </Card>
      </section>
    </AuthenticatedLayout>
  );
}

function KpiCard({ title, value }: { title: string; value: string | number }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-bold">{value}</p>
      </CardContent>
    </Card>
  );
}
