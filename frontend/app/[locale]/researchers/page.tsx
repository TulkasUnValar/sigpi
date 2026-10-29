"use client";

/**
 * Researchers list — paginated table with role-gated create CTA.
 *
 * Spec (researchers-ui list):
 *   - /researchers renders the paginated list (25/page) with completeness
 *     bars, status badges, and row actions.
 *   - Zero researchers → empty state with a create action.
 *   - Create is director+ (level ≤ 3): director, admin, superadmin.
 */

import { useState } from "react";
import Link from "next/link";
import { Plus, Users } from "lucide-react";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { RoleGuard } from "@/components/shell/RoleGuard";
import { ResearcherList } from "@/features/researchers/ResearcherList";
import { useResearchersList } from "@/features/researchers/queries";

/** Roles allowed to create researchers (director+, level ≤ 3). */
const CREATE_ROLES = ["director", "admin", "superadmin"];

export default function ResearchersPage() {
  const [page, setPage] = useState(1);
  const listQuery = useResearchersList({ page });

  const data = listQuery.data;
  const researchers = data?.results ?? [];
  const loading = listQuery.isLoading;

  return (
    <AuthenticatedLayout>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Investigadores</h1>
        <RoleGuard allowedRoles={CREATE_ROLES}>
          <Button asChild>
            <Link href="/researchers/new">
              <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
              Crear investigador
            </Link>
          </Button>
        </RoleGuard>
      </div>

      {loading ? (
        <div role="status" aria-label="Cargando investigadores" className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-12" />
          ))}
        </div>
      ) : researchers.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No hay investigadores"
          description="Crea el primer investigador para comenzar a gestionar los perfiles."
          action={
            <RoleGuard allowedRoles={CREATE_ROLES}>
              <Button asChild>
                <Link href="/researchers/new">Crear investigador</Link>
              </Button>
            </RoleGuard>
          }
        />
      ) : (
        <ResearcherList
          researchers={researchers}
          loading={loading}
          page={page}
          count={data?.count ?? researchers.length}
          hasNext={Boolean(data?.next)}
          hasPrevious={Boolean(data?.previous)}
          onPageChange={setPage}
        />
      )}
    </AuthenticatedLayout>
  );
}
