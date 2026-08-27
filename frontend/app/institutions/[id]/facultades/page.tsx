"use client";

/**
 * Facultades list — child entities of the institution (RF-F03).
 *
 * Optional ?sede= search param narrows the list. Create CTA is
 * admin/superadmin only (RF-F05).
 */

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { GraduationCap, Plus } from "lucide-react";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { RoleGuard } from "@/components/shell/RoleGuard";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { useFacultades } from "@/features/institutions/queries";

export default function FacultadesPage() {
  const params = useParams<{ id: string }>();
  const instId = params.id;
  const searchParams = useSearchParams();
  const sedeFilter = searchParams.get("sede") ?? undefined;

  const facultadesQuery = useFacultades(instId, sedeFilter);
  const facultades = facultadesQuery.data?.results ?? [];

  return (
    <AuthenticatedLayout>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Facultades</h1>
        <RoleGuard allowedRoles={["admin", "superadmin"]}>
          <Button asChild>
            <Link href={`/institutions/${instId}/facultades/new`}>
              <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
              Nueva facultad
            </Link>
          </Button>
        </RoleGuard>
      </div>

      {facultadesQuery.isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-14" />
          ))}
        </div>
      ) : facultades.length === 0 ? (
        <EmptyState
          icon={GraduationCap}
          title="No hay facultades"
          description="Crea la primera facultad de esta institución."
          action={
            <RoleGuard allowedRoles={["admin", "superadmin"]}>
              <Button asChild>
                <Link href={`/institutions/${instId}/facultades/new`}>Crear facultad</Link>
              </Button>
            </RoleGuard>
          }
        />
      ) : (
        <ul className="space-y-2">
          {facultades.map((facultad) => (
            <li
              key={facultad.id}
              className="flex items-center justify-between gap-3 rounded-md border p-3"
            >
              <div>
                <Link
                  href={`/institutions/${instId}/facultades/${facultad.id}`}
                  className="font-medium hover:underline"
                >
                  {facultad.name}
                </Link>
                <div className="text-xs text-muted-foreground">{facultad.code}</div>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={facultad.status} />
                <Button asChild variant="ghost" size="sm">
                  <Link href={`/institutions/${instId}/facultades/${facultad.id}/edit`}>
                    Editar
                  </Link>
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </AuthenticatedLayout>
  );
}