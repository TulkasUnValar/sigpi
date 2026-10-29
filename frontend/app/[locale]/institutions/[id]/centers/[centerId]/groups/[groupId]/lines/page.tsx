"use client";

/**
 * Lines list — leaf entities of a research group (RF-F03).
 *
 * GET /api/groups/{groupId}/lines/. Create CTA is gated to
 * director/admin/superadmin (RF-F05).
 */

import Link from "next/link";
import { useParams } from "next/navigation";
import { GitBranch, Plus } from "lucide-react";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { RoleGuard } from "@/components/shell/RoleGuard";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { useResearchLines } from "@/features/institutions/queries";

export default function LinesPage() {
  const params = useParams<{ id: string; centerId: string; groupId: string }>();
  const { id, centerId, groupId } = params;

  const linesQuery = useResearchLines(groupId);
  const lines = linesQuery.data?.results ?? [];

  const base = `/institutions/${id}/centers/${centerId}/groups/${groupId}`;

  return (
    <AuthenticatedLayout>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Líneas de investigación</h1>
        <RoleGuard allowedRoles={["director", "admin", "superadmin"]}>
          <Button asChild>
            <Link href={`${base}/lines/new`}>
              <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
              Nueva línea
            </Link>
          </Button>
        </RoleGuard>
      </div>

      {linesQuery.isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-14" />
          ))}
        </div>
      ) : lines.length === 0 ? (
        <EmptyState
          icon={GitBranch}
          title="No hay líneas de investigación"
          description="Crea la primera línea de investigación de este grupo."
          action={
            <RoleGuard allowedRoles={["director", "admin", "superadmin"]}>
              <Button asChild>
                <Link href={`${base}/lines/new`}>Crear línea</Link>
              </Button>
            </RoleGuard>
          }
        />
      ) : (
        <ul className="space-y-2">
          {lines.map((line) => (
            <li
              key={line.id}
              className="flex items-center justify-between gap-3 rounded-md border p-3"
            >
              <div>
                <Link href={`${base}/lines/${line.id}`} className="font-medium hover:underline">
                  {line.name}
                </Link>
                <div className="text-xs text-muted-foreground">{line.code}</div>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={line.status} />
                <Button asChild variant="ghost" size="sm">
                  <Link href={`${base}/lines/${line.id}/edit`}>Editar</Link>
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </AuthenticatedLayout>
  );
}
