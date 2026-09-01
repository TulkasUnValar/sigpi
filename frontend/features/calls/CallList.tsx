"use client";

/**
 * CallList — paginated calls table with empty state, filter UI and a
 * director-gated create CTA.
 *
 * Spec (calls-ui list):
 *   - Rows render title, StatusBadge, call_type label and created_at.
 *   - Pagination controls are driven by the DRF next/previous links.
 *   - The status/call_type filter controls render here; the refetch
 *     wiring lands with the PR3 slice.
 */

import { useState } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { useAuthStore } from "@/store/auth";
import { useCallsList } from "@/features/calls/queries";
import { canManageCall } from "@/features/calls/permissions";
import {
  CALL_STATUS_OPTIONS,
  CALL_TYPE_OPTIONS,
  getCallTypeLabel,
} from "@/features/calls/constants";

export function CallList() {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [callType, setCallType] = useState("");

  const { roles } = useAuthStore();
  const canCreate = canManageCall(roles);

  const callsQuery = useCallsList({ page });
  const data = callsQuery.data;
  const calls = data?.results ?? [];
  const loading = callsQuery.isLoading;

  const hasFilters = Boolean(status || callType);

  return (
    <>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Convocatorias</h1>
        {canCreate ? (
          <Button asChild>
            <Link href="/calls/new">Nueva convocatoria</Link>
          </Button>
        ) : null}
      </div>

      {/* Filters — UI present in PR1; refetch wiring lands in PR3 */}
      <Card className="mb-6">
        <CardContent className="grid gap-4 p-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="call-filter-status">Estado</Label>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger id="call-filter-status" aria-label="Estado">
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                {CALL_STATUS_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="call-filter-type">Tipo</Label>
            <Select value={callType} onValueChange={setCallType}>
              <SelectTrigger id="call-filter-type" aria-label="Tipo de convocatoria">
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                {CALL_TYPE_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-12" />
          ))}
        </div>
      ) : calls.length === 0 ? (
        <EmptyState
          title={hasFilters ? "Sin resultados" : "No hay convocatorias"}
          description={
            hasFilters
              ? "No se encontraron convocatorias con los filtros aplicados."
              : "Crea tu primera convocatoria para comenzar."
          }
          action={
            canCreate ? (
              <Button asChild variant="outline" size="sm">
                <Link href="/calls/new">Nueva convocatoria</Link>
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="overflow-hidden rounded-lg border">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/50 text-left">
              <tr>
                <th className="px-4 py-3 font-medium">Título</th>
                <th className="px-4 py-3 font-medium">Estado</th>
                <th className="px-4 py-3 font-medium">Tipo</th>
                <th className="px-4 py-3 font-medium">Creada</th>
              </tr>
            </thead>
            <tbody>
              {calls.map((c) => (
                <tr key={c.id} className="border-b last:border-0">
                  <td className="px-4 py-3">
                    <Link
                      href={`/calls/${c.id}`}
                      className="font-medium hover:underline"
                    >
                      {c.title}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="px-4 py-3">{getCallTypeLabel(c.call_type)}</td>
                  <td className="px-4 py-3">{c.created_at.slice(0, 10)}</td>
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
          {data?.count !== undefined ? ` · ${data.count} convocatorias` : ""}
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
    </>
  );
}