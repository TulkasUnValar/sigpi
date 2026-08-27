"use client";

/**
 * Institution detail — EntityDetail + FsmActionBar + StatusBadge.
 *
 * Spec (institutions-ui RF-F02/RF-F04):
 *   - Detail loads without an active institution (root entity).
 *   - FSM transitions (activate/deactivate/archive) exposed per role.
 */

import { useParams } from "next/navigation";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { EntityDetail } from "@/features/institutions/EntityDetail";
import { useInstitutionDetail } from "@/features/institutions/queries";

export default function InstitutionDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const detailQuery = useInstitutionDetail(id);

  if (detailQuery.isLoading) {
    return (
      <AuthenticatedLayout>
        <Skeleton className="mb-4 h-8 w-64" />
        <Skeleton className="h-64" />
      </AuthenticatedLayout>
    );
  }

  const institution = detailQuery.data;
  if (!institution) {
    return (
      <AuthenticatedLayout>
        <EmptyState title="Institución no encontrada" />
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <EntityDetail institution={institution} />
    </AuthenticatedLayout>
  );
}
