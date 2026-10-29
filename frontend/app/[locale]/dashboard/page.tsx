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
import { formatCurrency } from "@/features/budgets/constants";

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
            <KpiCard title="Presupuesto aprobado" value={formatCurrency(indicators["IND-007"])} />
            <KpiCard title="Presupuesto ejecutado" value={formatCurrency(indicators["IND-008"])} />
            <KpiCard title="Saldo presupuestal" value={formatCurrency(indicators["IND-009"])} />
            <ProfileCompletenessCard data={indicators["IND-012"]} />
            <KpiCard title="Proyectos en convocatorias externas" value={indicators["IND-014"]} />
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

      {/* Productos destacados */}
      <section className="mt-8 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Top proyectos con más productos</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="max-h-64 overflow-y-auto">
              <table className="w-full">
                <thead className="border-b bg-muted/50">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium">Proyecto</th>
                    <th className="px-4 py-3 text-right font-medium">Productos</th>
                  </tr>
                </thead>
                <tbody>
                  {indicators["IND-010"].slice(0, 5).map((item) => (
                    <tr key={item.project_id} className="border-b">
                      <td className="px-4 py-3">{item.name}</td>
                      <td className="px-4 py-3 text-right">{item.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top investigadores con más productos</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="max-h-64 overflow-y-auto">
              <table className="w-full">
                <thead className="border-b bg-muted/50">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium">Investigador</th>
                    <th className="px-4 py-3 text-right font-medium">Productos</th>
                  </tr>
                </thead>
                <tbody>
                  {indicators["IND-011"].slice(0, 5).map((item) => (
                    <tr key={item.researcher_id} className="border-b">
                      <td className="px-4 py-3">{item.full_name}</td>
                      <td className="px-4 py-3 text-right">{item.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
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

function ProfileCompletenessCard({
  data,
}: {
  data: { total: number; complete: number; rate: number };
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Perfiles completos
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-bold">{data.rate.toFixed(1)}%</p>
        <p className="mt-2 text-sm text-muted-foreground">
          {data.complete} de {data.total} investigadores
        </p>
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-all"
            style={{ width: `${Math.min(100, Math.max(0, data.rate))}%` }}
          />
        </div>
      </CardContent>
    </Card>
  );
}
