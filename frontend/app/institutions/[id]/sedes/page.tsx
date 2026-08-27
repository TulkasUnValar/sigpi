"use client";

/**
 * Sedes list — child entities of the institution (RF-F03).
 *
 * Parent id comes from the URL params; the list loads without the
 * X-Institution-ID header. Create CTA is admin/superadmin only (RF-F05).
 */

import Link from "next/link";
import { useParams } from "next/navigation";
import { MapPin, Plus } from "lucide-react";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { RoleGuard } from "@/components/shell/RoleGuard";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { useSedes } from "@/features/institutions/queries";

export default function SedesPage() {
  const params = useParams<{ id: string }>();
  const instId = params.id;

  const sedesQuery = useSedes(instId);
  const sedes = sedesQuery.data?.results ?? [];

  return (
    <AuthenticatedLayout>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Sedes</h1>
        <RoleGuard allowedRoles={["admin", "superadmin"]}>
          <Button asChild>
            <Link href={`/institutions/${instId}/sedes/new`}>
              <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
              Nueva sede
            </Link>
          </Button>
        </RoleGuard>
      </div>

      {sedesQuery.isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-14" />
          ))}
        </div>
      ) : sedes.length === 0 ? (
        <EmptyState
          icon={MapPin}
          title="No hay sedes"
          description="Crea la primera sede de esta institución."
          action={
            <RoleGuard allowedRoles={["admin", "superadmin"]}>
              <Button asChild>
                <Link href={`/institutions/${instId}/sedes/new`}>Crear sede</Link>
              </Button>
            </RoleGuard>
          }
        />
      ) : (
        <ul className="space-y-2">
          {sedes.map((sede) => (
            <li
              key={sede.id}
              className="flex items-center justify-between gap-3 rounded-md border p-3"
            >
              <div>
                <Link
                  href={`/institutions/${instId}/sedes/${sede.id}`}
                  className="font-medium hover:underline"
                >
                  {sede.name}
                </Link>
                <div className="text-xs text-muted-foreground">{sede.code}</div>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={sede.status} />
                <Button asChild variant="ghost" size="sm">
                  <Link href={`/institutions/${instId}/sedes/${sede.id}/edit`}>Editar</Link>
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </AuthenticatedLayout>
  );
}