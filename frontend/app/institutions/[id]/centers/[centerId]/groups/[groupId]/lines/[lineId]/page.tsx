"use client";

/**
 * Line detail — generic EntityDetail + kind-specific FsmActionBar.
 *
 * Spec (institutions-ui RF-F03/RF-F04):
 *   - FSM transitions POST to /api/lines/{id}/{action}/.
 *   - FSM actions are visible for director/admin/superadmin (RF-F05).
 */

import { useParams } from "next/navigation";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { EntityDetail } from "@/features/institutions/EntityDetail";
import { FsmActionBar } from "@/features/institutions/FsmActionBar";
import { useResearchLineDetail } from "@/features/institutions/queries";
import { useResearchLineTransition } from "@/features/institutions/mutations";

export default function LineDetailPage() {
  const params = useParams<{ lineId: string }>();
  const { lineId } = params;

  const detailQuery = useResearchLineDetail(lineId);
  const transition = useResearchLineTransition();

  if (detailQuery.isLoading) {
    return (
      <AuthenticatedLayout>
        <Skeleton className="mb-4 h-8 w-64" />
        <Skeleton className="h-64" />
      </AuthenticatedLayout>
    );
  }

  const line = detailQuery.data;
  if (!line) {
    return (
      <AuthenticatedLayout>
        <EmptyState title="Línea no encontrada" />
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <EntityDetail
        title={line.name}
        status={line.status}
        actionBar={
          <FsmActionBar
            entityId={line.id}
            state={line.status}
            transition={transition}
            entityLabel="Línea de investigación"
            minRoles={["director", "admin", "superadmin"]}
          />
        }
        fields={[
          { label: "Código", value: line.code },
          { label: "Descripción", value: line.description },
          { label: "Creada", value: line.created_at },
          { label: "Actualizada", value: line.updated_at },
        ]}
      />
    </AuthenticatedLayout>
  );
}
