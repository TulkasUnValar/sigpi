"use client";

/**
 * Sede detail — generic EntityDetail + kind-specific FsmActionBar.
 *
 * Spec (institutions-ui RF-F03/RF-F04):
 *   - FSM transitions POST to /api/sedes/{id}/{action}/.
 *   - FSM actions are visible for admin/superadmin (RF-F05).
 */

import { useParams } from "next/navigation";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { EntityDetail } from "@/features/institutions/EntityDetail";
import { FsmActionBar } from "@/features/institutions/FsmActionBar";
import { useSedeDetail } from "@/features/institutions/queries";
import { useSedeTransition } from "@/features/institutions/mutations";

export default function SedeDetailPage() {
  const params = useParams<{ id: string; sedeId: string }>();
  const { sedeId } = params;

  const detailQuery = useSedeDetail(sedeId);
  const transition = useSedeTransition();

  if (detailQuery.isLoading) {
    return (
      <AuthenticatedLayout>
        <Skeleton className="mb-4 h-8 w-64" />
        <Skeleton className="h-64" />
      </AuthenticatedLayout>
    );
  }

  const sede = detailQuery.data;
  if (!sede) {
    return (
      <AuthenticatedLayout>
        <EmptyState title="Sede no encontrada" />
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <EntityDetail
        title={sede.name}
        status={sede.status}
        actionBar={
          <FsmActionBar
            entityId={sede.id}
            state={sede.status}
            transition={transition}
            entityLabel="Sede"
            minRoles={["admin", "superadmin"]}
          />
        }
        fields={[
          { label: "Código", value: sede.code },
          { label: "Descripción", value: sede.description },
          { label: "Creada", value: sede.created_at },
          { label: "Actualizada", value: sede.updated_at },
        ]}
      />
    </AuthenticatedLayout>
  );
}