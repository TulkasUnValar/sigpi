"use client";

/**
 * Groups list — child entities of a research center (RF-F03).
 *
 * GET /api/centers/{centerId}/groups/. Create CTA is gated to
 * director/admin/superadmin (RF-F05).
 */

import Link from "next/link";
import { useParams } from "next/navigation";
import { FlaskConical, Plus } from "lucide-react";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { RoleGuard } from "@/components/shell/RoleGuard";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { useResearchGroups } from "@/features/institutions/queries";

export default function GroupsPage() {
  const params = useParams<{ id: string; centerId: string }>();
  const { id, centerId } = params;

  const groupsQuery = useResearchGroups(centerId);
  const groups = groupsQuery.data?.results ?? [];

  return (
    <AuthenticatedLayout>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Grupos de investigación</h1>
        <RoleGuard allowedRoles={["director", "admin", "superadmin"]}>
          <Button asChild>
            <Link href={`/institutions/${id}/centers/${centerId}/groups/new`}>
              <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
              Nuevo grupo
            </Link>
          </Button>
        </RoleGuard>
      </div>

      {groupsQuery.isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-14" />
          ))}
        </div>
      ) : groups.length === 0 ? (
        <EmptyState
          icon={FlaskConical}
          title="No hay grupos de investigación"
          description="Crea el primer grupo de investigación de este centro."
          action={
            <RoleGuard allowedRoles={["director", "admin", "superadmin"]}>
              <Button asChild>
                <Link href={`/institutions/${id}/centers/${centerId}/groups/new`}>Crear grupo</Link>
              </Button>
            </RoleGuard>
          }
        />
      ) : (
        <ul className="space-y-2">
          {groups.map((group) => (
            <li
              key={group.id}
              className="flex items-center justify-between gap-3 rounded-md border p-3"
            >
              <div>
                <Link
                  href={`/institutions/${id}/centers/${centerId}/groups/${group.id}`}
                  className="font-medium hover:underline"
                >
                  {group.name}
                </Link>
                <div className="text-xs text-muted-foreground">{group.code}</div>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={group.status} />
                <Button asChild variant="ghost" size="sm">
                  <Link href={`/institutions/${id}/centers/${centerId}/groups/${group.id}/edit`}>
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
