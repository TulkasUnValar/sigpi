"use client";

/**
 * Projects list — paginated table with status/center/year/search filters.
 *
 * Spec (projects-ui list):
 *   /projects renders a paginated table (DRF 25/page) with filters and
 *   page controls driven by the DRF `next`/`previous` links.
 */

import { useState } from "react";
import Link from "next/link";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
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
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { StatusBadge } from "@/components/shared/StatusBadge";
import {
  useProjectsList,
  useCenters,
} from "@/features/projects/queries";

const STATUS_OPTIONS = [
  { value: "borrador", label: "Borrador" },
  { value: "enviado", label: "Enviado" },
  { value: "en_revision", label: "En revisión" },
  { value: "observado", label: "Observado" },
  { value: "aprobado", label: "Aprobado" },
  { value: "en_ejecucion", label: "En ejecución" },
  { value: "suspendido", label: "Suspendido" },
  { value: "finalizado", label: "Finalizado" },
  { value: "en_cierre", label: "En cierre" },
  { value: "cerrado", label: "Cerrado" },
  { value: "rechazado", label: "Rechazado" },
  { value: "cancelado", label: "Cancelado" },
];

export default function ProjectsPage() {
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
    <AuthenticatedLayout>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Proyectos</h1>
        <Button asChild>
          <Link href="/projects/new">Nuevo proyecto</Link>
        </Button>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardContent className="grid gap-4 p-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <Label htmlFor="filter-status">Estado</Label>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger id="filter-status" aria-label="Estado">
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="filter-center">Centro</Label>
            <Select value={center} onValueChange={setCenter}>
              <SelectTrigger id="filter-center" aria-label="Centro">
                <SelectValue placeholder="Todos" />
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
            <Label htmlFor="filter-year">Año</Label>
            <Input
              id="filter-year"
              type="number"
              placeholder="2026"
              value={year}
              onChange={(e) => setYear(e.target.value)}
            />
          </div>

          <div>
            <Label htmlFor="filter-search">Búsqueda</Label>
            <Input
              id="filter-search"
              placeholder="Título, resumen…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-12" />
          ))}
        </div>
      ) : projects.length === 0 ? (
        <EmptyState
          title={hasFilters ? "Sin resultados" : "No hay proyectos"}
          description={
            hasFilters
              ? "No se encontraron proyectos con los filtros aplicados."
              : "Crea tu primer proyecto para comenzar."
          }
        />
      ) : (
        <div className="overflow-hidden rounded-lg border">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/50 text-left">
              <tr>
                <th className="px-4 py-3 font-medium">Título</th>
                <th className="px-4 py-3 font-medium">Estado</th>
                <th className="px-4 py-3 font-medium">Inicio</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr key={p.id} className="border-b last:border-0">
                  <td className="px-4 py-3">
                    <Link
                      href={`/projects/${p.id}`}
                      className="font-medium hover:underline"
                    >
                      {p.title}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={p.status} />
                  </td>
                  <td className="px-4 py-3">{p.start_date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination driven by DRF next/previous links */}
      <div className="mt-4 flex items-center justify-between">
        <Button
          variant="outline"
          size="sm"
          disabled={!data?.previous || loading}
          onClick={() => setPage((p) => Math.max(1, p - 1))}
        >
          Anterior
        </Button>
        <span className="text-sm text-muted-foreground">
          Página {page}
          {data?.count !== undefined ? ` · ${data.count} proyectos` : ""}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={!data?.next || loading}
          onClick={() => setPage((p) => p + 1)}
        >
          Siguiente
        </Button>
      </div>
    </AuthenticatedLayout>
  );
}
