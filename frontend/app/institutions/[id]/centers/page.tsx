"use client";

/**
 * Centers list — child entities of the institution (RF-F03).
 *
 * Optional ?parent_type=&parent= search params narrow the list
 * (institution | sede | facultad). Create CTA is admin/superadmin (RF-F05).
 */

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { FlaskConical, Plus } from "lucide-react";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { RoleGuard } from "@/components/shell/RoleGuard";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { useResearchCenters } from "@/features/institutions/queries";

export default function CentersPage() {
  const params = useParams<{ id: string }>();
  const instId = params.id;
  const searchParams = useSearchParams();
  const parentType = searchParams.get("parent_type") ?? undefined;
  const parent = searchParams.get("parent") ?? undefined;

  const centersQuery = useResearchCenters(instId, parentType, parent);
  const centers = centersQuery.data?.results ?? [];

  return (
    <AuthenticatedLayout>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Centros de investigación</h1>
        <RoleGuard allowedRoles={["admin", "superadmin"]}>
          <Button asChild>
            <Link href={`/institutions/${instId}/centers/new`}>
              <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
              Nuevo centro
            </Link>
          </Button>
        </RoleGuard>
      </div>

      {centersQuery.isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-14" />
          ))}
        </div>
      ) : centers.length === 0 ? (
        <EmptyState
          icon={FlaskConical}
          title="No hay centros de investigación"
          description="Crea el primer centro de investigación de esta institución."
          action={
            <RoleGuard allowedRoles={["admin", "superadmin"]}>
              <Button asChild>
                <Link href={`/institutions/${instId}/centers/new`}>Crear centro</Link>
              </Button>
            </RoleGuard>
          }
        />
      ) : (
        <ul className="space-y-2">
          {centers.map((center) => (
            <li
              key={center.id}
              className="flex items-center justify-between gap-3 rounded-md border p-3"
            >
              <div>
                <Link
                  href={`/institutions/${instId}/centers/${center.id}`}
                  className="font-medium hover:underline"
                >
                  {center.name}
                </Link>
                <div className="text-xs text-muted-foreground">{center.code}</div>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={center.status} />
                <Button asChild variant="ghost" size="sm">
                  <Link href={`/institutions/${instId}/centers/${center.id}/edit`}>Editar</Link>
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </AuthenticatedLayout>
  );
}