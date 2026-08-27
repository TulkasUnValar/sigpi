"use client";

/**
 * Center detail — generic EntityDetail + kind-specific FsmActionBar.
 *
 * Spec (institutions-ui RF-F03/RF-F04):
 *   - FSM transitions POST to /api/centers/{id}/{action}/.
 *   - FSM actions are visible for admin/superadmin (RF-F05).
 */

import { useParams } from "next/navigation";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { EntityDetail } from "@/features/institutions/EntityDetail";
import { FsmActionBar } from "@/features/institutions/FsmActionBar";
import { useCenterDetail } from "@/features/institutions/queries";
import { useCenterTransition } from "@/features/institutions/mutations";

export default function CenterDetailPage() {
  const params = useParams<{ id: string; centerId: string }>();
  const { id, centerId } = params;

  const detailQuery = useCenterDetail(centerId);
  const transition = useCenterTransition();

  if (detailQuery.isLoading) {
    return (
      <AuthenticatedLayout>
        <Skeleton className="mb-4 h-8 w-64" />
        <Skeleton className="h-64" />
      </AuthenticatedLayout>
    );
  }

  const center = detailQuery.data;
  if (!center) {
    return (
      <AuthenticatedLayout>
        <EmptyState title="Centro no encontrado" />
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <EntityDetail
        title={center.name}
        status={center.status}
        actionBar={
          <FsmActionBar
            entityId={center.id}
            state={center.status}
            transition={transition}
            entityLabel="Centro de investigación"
            minRoles={["admin", "superadmin"]}
          />
        }
        fields={[
          { label: "Sede", value: center.sede ?? "—" },
          { label: "Facultad", value: center.facultad ?? "—" },
          { label: "Código", value: center.code },
          { label: "Descripción", value: center.description },
          { label: "Correo de contacto", value: center.contact_email },
          { label: "Teléfono de contacto", value: center.contact_phone },
          { label: "Creado", value: center.created_at },
          { label: "Actualizado", value: center.updated_at },
        ]}
      />
    </AuthenticatedLayout>
  );
}