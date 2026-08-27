"use client";

/**
 * Institutions list — hierarchy tree with EmptyState bootstrap.
 *
 * Spec (institutions-ui RF-F01/RF-F02):
 *   - Root institutions render as a tree; each node shows status badge.
 *   - Zero institutions → EmptyState with a create CTA.
 *   - List loads WITHOUT an active institution (bootstrap — no membership).
 *   - Institution create is superadmin-only (backend IsSuperAdmin).
 */

import Link from "next/link";
import { Building2, Plus } from "lucide-react";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { RoleGuard } from "@/components/shell/RoleGuard";
import { InstitutionTree } from "@/features/institutions/InstitutionTree";
import { useInstitutionsList } from "@/features/institutions/queries";
import type { InstitutionTreeNode } from "@/features/institutions/types";

export default function InstitutionsPage() {
  const listQuery = useInstitutionsList();
  const institutions = listQuery.data?.results ?? [];

  // PR1 renders root institutions; children arrive in PR2/PR3.
  const nodes: InstitutionTreeNode[] = institutions.map((inst) => ({
    id: inst.id,
    kind: "institution",
    name: inst.name,
    code: inst.code,
    status: inst.status,
    is_active: inst.is_active,
    children: [],
  }));

  return (
    <AuthenticatedLayout>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Estructura institucional</h1>
        <RoleGuard allowedRoles={["superadmin"]}>
          <Button asChild>
            <Link href="/institutions/new">
              <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
              Nueva institución
            </Link>
          </Button>
        </RoleGuard>
      </div>

      {listQuery.isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-10" />
          ))}
        </div>
      ) : institutions.length === 0 ? (
        <EmptyState
          icon={Building2}
          title="No hay instituciones"
          description="Crea la primera institución para comenzar a estructurar el sistema."
          action={
            <RoleGuard allowedRoles={["superadmin"]}>
              <Button asChild>
                <Link href="/institutions/new">Crear institución</Link>
              </Button>
            </RoleGuard>
          }
        />
      ) : (
        <InstitutionTree nodes={nodes} />
      )}
    </AuthenticatedLayout>
  );
}
