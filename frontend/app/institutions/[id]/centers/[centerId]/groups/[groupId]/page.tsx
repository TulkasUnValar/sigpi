"use client";

/**
 * Group detail — generic EntityDetail + kind-specific FsmActionBar.
 *
 * Spec (institutions-ui RF-F03/RF-F04):
 *   - FSM transitions POST to /api/groups/{id}/{action}/.
 *   - FSM actions are visible for director/admin/superadmin (RF-F05).
 */

import { useParams } from "next/navigation";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { EntityDetail } from "@/features/institutions/EntityDetail";
import { FsmActionBar } from "@/features/institutions/FsmActionBar";
import { useResearchGroupDetail } from "@/features/institutions/queries";
import { useResearchGroupTransition } from "@/features/institutions/mutations";

export default function GroupDetailPage() {
  const params = useParams<{ groupId: string }>();
  const { groupId } = params;

  const detailQuery = useResearchGroupDetail(groupId);
  const transition = useResearchGroupTransition();

  if (detailQuery.isLoading) {
    return (
      <AuthenticatedLayout>
        <Skeleton className="mb-4 h-8 w-64" />
        <Skeleton className="h-64" />
      </AuthenticatedLayout>
    );
  }

  const group = detailQuery.data;
  if (!group) {
    return (
      <AuthenticatedLayout>
        <EmptyState title="Grupo no encontrado" />
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <EntityDetail
        title={group.name}
        status={group.status}
        actionBar={
          <FsmActionBar
            entityId={group.id}
            state={group.status}
            transition={transition}
            entityLabel="Grupo de investigación"
            minRoles={["director", "admin", "superadmin"]}
          />
        }
        fields={[
          { label: "Código", value: group.code },
          { label: "Descripción", value: group.description },
          { label: "Creado", value: group.created_at },
          { label: "Actualizado", value: group.updated_at },
        ]}
      />
    </AuthenticatedLayout>
  );
}
