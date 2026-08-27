"use client";

/**
 * Facultad detail — generic EntityDetail + kind-specific FsmActionBar.
 *
 * Spec (institutions-ui RF-F03/RF-F04):
 *   - FSM transitions POST to /api/facultades/{id}/{action}/.
 *   - FSM actions are visible for admin/superadmin (RF-F05).
 */

import { useParams } from "next/navigation";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { EntityDetail } from "@/features/institutions/EntityDetail";
import { FsmActionBar } from "@/features/institutions/FsmActionBar";
import { useFacultadDetail } from "@/features/institutions/queries";
import { useFacultadTransition } from "@/features/institutions/mutations";

export default function FacultadDetailPage() {
  const params = useParams<{ id: string; facultadId: string }>();
  const { id, facultadId } = params;

  const detailQuery = useFacultadDetail(facultadId);
  const transition = useFacultadTransition();

  if (detailQuery.isLoading) {
    return (
      <AuthenticatedLayout>
        <Skeleton className="mb-4 h-8 w-64" />
        <Skeleton className="h-64" />
      </AuthenticatedLayout>
    );
  }

  const facultad = detailQuery.data;
  if (!facultad) {
    return (
      <AuthenticatedLayout>
        <EmptyState title="Facultad no encontrada" />
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <EntityDetail
        title={facultad.name}
        status={facultad.status}
        actionBar={
          <FsmActionBar
            entityId={facultad.id}
            state={facultad.status}
            transition={transition}
            entityLabel="Facultad"
            minRoles={["admin", "superadmin"]}
          />
        }
        fields={[
          { label: "Sede", value: facultad.sede ?? "—" },
          { label: "Código", value: facultad.code },
          { label: "Descripción", value: facultad.description },
          { label: "Creada", value: facultad.created_at },
          { label: "Actualizada", value: facultad.updated_at },
        ]}
      />
    </AuthenticatedLayout>
  );
}