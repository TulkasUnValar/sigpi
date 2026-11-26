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
import { useTranslations } from "next-intl";

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
  const t = useTranslations("researchers");

  const data = listQuery.data;
  const researchers = data?.results ?? [];
  const loading = listQuery.isLoading;

  return (
    <AuthenticatedLayout>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        <RoleGuard allowedRoles={CREATE_ROLES}>
          <Button asChild>
            <Link href="/researchers/new">
              <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
              {t("createNew")}
            </Link>
          </Button>
        </RoleGuard>
      </div>

      {loading ? (
        <div role="status" aria-label={t("loading")} className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-12" />
          ))}
        </div>
      ) : researchers.length === 0 ? (
        <EmptyState
          icon={Users}
          title={t("noResearchers")}
          description={t("noResearchersDescription")}
          action={
            <RoleGuard allowedRoles={CREATE_ROLES}>
              <Button asChild>
                <Link href="/researchers/new">{t("createNew")}</Link>
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
