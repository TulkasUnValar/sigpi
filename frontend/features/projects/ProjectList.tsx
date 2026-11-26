"use client";

/**
 * ProjectList — paginated projects table with status/center/year/search
 * filters and DRF next/previous page controls.
 *
 * Spec (projects-ui list / FR-02):
 *   /projects renders a paginated table (DRF 25/page) with filters and
 *   page controls driven by the DRF `next`/`previous` links.
 */

import { useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { FolderKanban, Plus, Filter, ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { PageHeader } from "@/components/shared/PageHeader";
import { useProjectsList, useCenters } from "@/features/projects/queries";

const STATUS_OPTIONS = [
  { value: "borrador", labelKey: "status.borrador" },
  { value: "enviado", labelKey: "status.enviado" },
  { value: "en_revision", labelKey: "status.en_revision" },
  { value: "observado", labelKey: "status.observado" },
  { value: "aprobado", labelKey: "status.aprobado" },
  { value: "en_ejecucion", labelKey: "status.en_ejecucion" },
  { value: "suspendido", labelKey: "status.suspendido" },
  { value: "finalizado", labelKey: "status.finalizado" },
  { value: "en_cierre", labelKey: "status.en_cierre" },
  { value: "cerrado", labelKey: "status.cerrado" },
  { value: "rechazado", labelKey: "status.rechazado" },
  { value: "cancelado", labelKey: "status.cancelado" },
];

// The component takes no props (design contract); the empty interface is
// intentional, so the repo's no-empty-object-type rule is disabled here.
// eslint-disable-next-line @typescript-eslint/no-empty-object-type
interface ProjectListProps {}

export function ProjectList(_props: ProjectListProps) {
  const t = useTranslations("projects");
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [center, setCenter] = useState("");
  const [year, setYear] = useState("");
  const [search, setSearch] = useState("");

  const centersQuery = useCenters();
  const projectsQuery = useProjectsList({ page, status, center, year, search });

  const data = projectsQuery.data;
  const projects = data?.results ?? [];
  const loading = projectsQuery.isLoading;

  const hasFilters = Boolean(status || center || year || search);

  return (
    <div className="animate-fade-in space-y-6">
      {/* Page header */}
      <PageHeader
        title={t("list.title")}
        description={t("list.description")}
        icon={FolderKanban}
        action={
          <Button asChild>
            <Link href="/projects/new">
              <Plus className="h-4 w-4" aria-hidden="true" />
              {t("list.createNew")}
            </Link>
          </Button>
        }
      />

      {/* Filters card */}
      <Card className="shadow-card">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            <CardTitle className="text-sm font-medium">{t("list.filtersTitle")}</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <Label htmlFor="filter-status">{t("list.filterStatus")}</Label>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger id="filter-status" aria-label={t("list.filterStatus")}>
                <SelectValue placeholder={t("list.placeholderAll")} />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {t(opt.labelKey)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="filter-center">{t("list.filterCenter")}</Label>
            <Select value={center} onValueChange={setCenter}>
              <SelectTrigger id="filter-center" aria-label={t("list.filterCenter")}>
                <SelectValue placeholder={t("list.placeholderAll")} />
              </SelectTrigger>
              <SelectContent>
                {(centersQuery.data ?? []).map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="filter-year">{t("list.filterYear")}</Label>
            <Input
              id="filter-year"
              type="number"
              placeholder={t("list.placeholderYear")}
              value={year}
              onChange={(e) => setYear(e.target.value)}
            />
          </div>

          <div>
            <Label htmlFor="filter-search">{t("list.filterSearch")}</Label>
            <Input
              id="filter-search"
              placeholder={t("list.placeholderSearch")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      {/* Content */}
      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-14 rounded-lg" />
          ))}
        </div>
      ) : projects.length === 0 ? (
        <EmptyState
          title={hasFilters ? t("list.noResults") : t("list.noProjects")}
          description={
            hasFilters ? t("list.noResultsDescription") : t("list.noProjectsDescription")
          }
          icon={FolderKanban}
        />
      ) : (
        <div className="overflow-hidden rounded-xl border bg-card shadow-card">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/50 text-left">
              <tr>
                <th className="px-4 py-3.5 font-medium text-muted-foreground">
                  {t("table.title")}
                </th>
                <th className="px-4 py-3.5 font-medium text-muted-foreground">
                  {t("table.status")}
                </th>
                <th className="px-4 py-3.5 font-medium text-muted-foreground">
                  {t("table.startDate")}
                </th>
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr
                  key={p.id}
                  className="border-b transition-colors last:border-0 hover:bg-muted/30"
                >
                  <td className="px-4 py-3.5">
                    <Link
                      href={`/projects/${p.id}`}
                      className="font-medium hover:text-primary hover:underline"
                    >
                      {p.title}
                    </Link>
                  </td>
                  <td className="px-4 py-3.5">
                    <StatusBadge status={p.status} />
                  </td>
                  <td className="px-4 py-3.5 text-muted-foreground">{p.start_date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          size="sm"
          disabled={!data?.previous || loading}
          onClick={() => setPage((p) => Math.max(1, p - 1))}
        >
          <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          {t("list.previous")}
        </Button>
        <span className="text-sm text-muted-foreground">
          {t("list.pageInfo", { page })}
          {data?.count !== undefined ? ` · ${t("list.countInfo", { count: data.count })}` : ""}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={!data?.next || loading}
          onClick={() => setPage((p) => p + 1)}
        >
          {t("list.next")}
          <ChevronRight className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}
