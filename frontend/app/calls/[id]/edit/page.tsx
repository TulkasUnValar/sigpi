"use client";

/**
 * Edit call page — shared CallForm seeded from the detail query.
 *
 * Spec (calls-ui edit): /calls/{id}/edit PATCHes /api/calls/{id}/ with the
 * same zod rules as create; status and institution are read-only.
 */

import { useParams } from "next/navigation";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { RoleGuard } from "@/components/shell/RoleGuard";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { CallForm } from "@/features/calls/CallForm";
import { MANAGER_ROLES } from "@/features/calls/permissions";
import { useCallDetail } from "@/features/calls/queries";

export default function EditCallPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const detailQuery = useCallDetail(id);

  if (detailQuery.isLoading) {
    return (
      <AuthenticatedLayout>
        <Skeleton className="mb-4 h-8 w-64" />
        <Skeleton className="h-64" />
      </AuthenticatedLayout>
    );
  }

  const call = detailQuery.data;
  if (!call) {
    return (
      <AuthenticatedLayout>
        <EmptyState title="Convocatoria no encontrada" />
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <RoleGuard allowedRoles={[...MANAGER_ROLES]}>
        <CallForm mode="edit" callId={id} initialValues={call} />
      </RoleGuard>
    </AuthenticatedLayout>
  );
}