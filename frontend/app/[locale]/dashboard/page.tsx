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

import { useTranslations } from "next-intl";
import { useAuthStore } from "@/store/auth";
import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { StatCard } from "@/components/shared/StatCard";
import { PageHeader } from "@/components/shared/PageHeader";
import { SectionCard } from "@/components/shared/SectionCard";
import { useDashboardSummary } from "@/features/dashboard/queries";
import { ProjectsByStatusChart } from "@/features/dashboard/charts/ProjectsByStatusChart";
import { ProjectsByCenterChart } from "@/features/dashboard/charts/ProjectsByCenterChart";
import { BudgetExecutionChart } from "@/features/dashboard/charts/BudgetExecutionChart";
import { ProgressReportsChart } from "@/features/dashboard/charts/ProgressReportsChart";
import { formatCurrency } from "@/features/budgets/constants";
import {
  LayoutDashboard,
  FolderKanban,
  Clock,
  TrendingUp,
  CheckCircle2,
  DollarSign,
  PiggyBank,
  Wallet,
  Users,
  Megaphone,
} from "lucide-react";

export default function DashboardPage() {
  const { roles, user } = useAuthStore();
  const isDirector =
    roles.includes("director") || roles.includes("admin") || roles.includes("auditor");

  const { data, isLoading, error } = useDashboardSummary();
  const t = useTranslations("dashboard");

  if (isLoading) {
    return (
      <AuthenticatedLayout>
        <div className="space-y-6">
          <Skeleton className="h-10 w-64" />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-32" />
            ))}
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
          title={t("errorTitle")}
          description={t("errorDescription")}
        />
      </AuthenticatedLayout>
    );
  }

  const { indicators, charts } = data;
  const userName = user?.email?.split("@")[0] || "";

  return (
    <AuthenticatedLayout>
      <div className="animate-fade-in space-y-6">
        {/* Welcome message */}
        <PageHeader
          title={t("title")}
          description={t("welcomeBack", { name: userName })}
          icon={LayoutDashboard}
        />

        {/* KPI Cards */}
        <section>
          <h2 className="mb-4 text-lg font-semibold">{t("kpiSectionTitle")}</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            {isDirector ? (
              <>
                <StatCard
                  title={t("kpi.totalProjects")}
                  value={indicators["IND-001"]}
                  icon={FolderKanban}
                />
                <StatCard
                  title={t("kpi.pendingApproval")}
                  value={indicators["IND-004"]}
                  icon={Clock}
                />
                <StatCard
                  title={t("kpi.pendingAdvances")}
                  value={indicators["IND-005"]}
                  icon={Clock}
                />
                <StatCard
                  title={t("kpi.avgProgress")}
                  value={`${indicators["IND-006"].toFixed(1)}%`}
                  icon={TrendingUp}
                />
                <StatCard
                  title={t("kpi.completeProjects")}
                  value={indicators["IND-013"]}
                  icon={CheckCircle2}
                />
                <StatCard
                  title={t("kpi.approvedBudget")}
                  value={formatCurrency(indicators["IND-007"])}
                  icon={DollarSign}
                />
                <StatCard
                  title={t("kpi.executedBudget")}
                  value={formatCurrency(indicators["IND-008"])}
                  icon={Wallet}
                />
                <StatCard
                  title={t("kpi.budgetBalance")}
                  value={formatCurrency(indicators["IND-009"])}
                  icon={PiggyBank}
                />
                <ProfileCompletenessCard data={indicators["IND-012"]} />
                <StatCard
                  title={t("kpi.externalCalls")}
                  value={indicators["IND-014"]}
                  icon={Megaphone}
                />
              </>
            ) : (
              <>
                <StatCard
                  title={t("kpi.myProjects")}
                  value={indicators["IND-001"]}
                  icon={FolderKanban}
                />
                <StatCard
                  title={t("kpi.avgProgress")}
                  value={`${indicators["IND-006"].toFixed(1)}%`}
                  icon={TrendingUp}
                />
              </>
            )}
          </div>
        </section>

        {/* Charts */}
        <section className="grid gap-6 lg:grid-cols-2">
          <SectionCard title={t("chart.projectsByStatus")} icon={FolderKanban}>
            <ProjectsByStatusChart data={charts.projects_by_status} />
          </SectionCard>

          <SectionCard title={t("chart.projectsByCenter")} icon={Users}>
            <ProjectsByCenterChart data={charts.projects_by_center} />
          </SectionCard>

          <SectionCard title={t("chart.budgetExecution")} icon={DollarSign}>
            <BudgetExecutionChart data={charts.budget} />
          </SectionCard>

          <SectionCard title={t("chart.progressReports")} icon={TrendingUp}>
            <ProgressReportsChart data={charts.progress_reports} />
          </SectionCard>
        </section>

        {/* Top tables */}
        <section className="grid gap-6 lg:grid-cols-2">
          <div className="card-attio rounded-xl">
            <div className="border-b border-border-subtle p-4 dark:border-border-default">
              <h3 className="text-base font-semibold">
                {t("top.projectsWithProducts")}
              </h3>
            </div>
            <div className="p-0">
              <div className="max-h-64 overflow-y-auto scrollbar-thin">
                <table className="table-attio table-compact w-full">
                  <thead>
                    <tr>
                      <th className="text-left">
                        {t("table.project")}
                      </th>
                      <th className="text-right">
                        {t("table.products")}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {indicators["IND-010"].slice(0, 5).map((item) => (
                      <tr
                        key={item.project_id}
                        className="border-b border-border-subtle transition-colors last:border-0 hover:bg-surface-50 dark:border-border-default dark:hover:bg-surface-100"
                      >
                        <td className="font-medium">{item.name}</td>
                        <td className="text-right">
                          <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-surface-100 text-xs font-semibold text-foreground dark:bg-surface-200">
                            {item.count}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div className="card-attio rounded-xl">
            <div className="border-b border-border-subtle p-4 dark:border-border-default">
              <h3 className="text-base font-semibold">
                {t("top.researchersWithProducts")}
              </h3>
            </div>
            <div className="p-0">
              <div className="max-h-64 overflow-y-auto scrollbar-thin">
                <table className="table-attio table-compact w-full">
                  <thead>
                    <tr>
                      <th className="text-left">
                        {t("table.researcher")}
                      </th>
                      <th className="text-right">
                        {t("table.products")}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {indicators["IND-011"].slice(0, 5).map((item) => (
                      <tr
                        key={item.researcher_id}
                        className="border-b border-border-subtle transition-colors last:border-0 hover:bg-surface-50 dark:border-border-default dark:hover:bg-surface-100"
                      >
                        <td className="font-medium">{item.full_name}</td>
                        <td className="text-right">
                          <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-surface-100 text-xs font-semibold text-foreground dark:bg-surface-200">
                            {item.count}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </section>
      </div>
    </AuthenticatedLayout>
  );
}

function ProfileCompletenessCard({
  data,
}: {
  data: { total: number; complete: number; rate: number };
}) {
  const t = useTranslations("dashboard");
  return (
    <Card className="card-attio rounded-xl">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-xs font-medium uppercase tracking-wider text-gray-500">
          {t("profileCompleteness.title")}
        </CardTitle>
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-surface-100 dark:bg-surface-200">
          <Users className="h-4 w-4 text-foreground" aria-hidden="true" />
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-semibold tracking-tight">{data.rate.toFixed(1)}%</p>
        <p className="mt-1 text-xs text-gray-500">
          {t("profileCompleteness.researchers", {
            complete: data.complete,
            total: data.total,
          })}
        </p>
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-surface-100 dark:bg-surface-200">
          <div
            className="h-full rounded-full bg-foreground transition-all dark:bg-ink-900"
            style={{ width: `${Math.min(100, Math.max(0, data.rate))}%` }}
          />
        </div>
      </CardContent>
    </Card>
  );
}
