"use client";

/**
 * Center edit — generic EntityForm prefilled from the detail; PATCH
 * /api/centers/{id}/. Sede/facultad references are selectable.
 */

import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { RoleGuard } from "@/components/shell/RoleGuard";
import { getErrorMessage } from "@/lib/errors";
import { EntityForm } from "@/features/institutions/EntityForm";
import { centerConfig, type CenterFormValues } from "@/features/institutions/schemas";
import { useCenterDetail, useFacultades, useSedes } from "@/features/institutions/queries";
import { useUpdateCenter } from "@/features/institutions/mutations";
import type { EntityFieldOption } from "@/features/institutions/types";

export default function EditCenterPage() {
  const params = useParams<{ id: string; centerId: string }>();
  const { id, centerId } = params;
  const router = useRouter();

  const detailQuery = useCenterDetail(centerId);
  const updateCenter = useUpdateCenter();
  const sedesQuery = useSedes(id);
  const facultadesQuery = useFacultades(id);

  const sedeOptions: EntityFieldOption[] = (sedesQuery.data?.results ?? []).map((sede) => ({
    value: sede.id,
    label: sede.name,
  }));
  const facultadOptions: EntityFieldOption[] = (facultadesQuery.data?.results ?? []).map(
    (facultad) => ({
      value: facultad.id,
      label: facultad.name,
    }),
  );

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

  const defaultValues: CenterFormValues = {
    sede: center.sede ?? "",
    facultad: center.facultad ?? "",
    code: center.code,
    name: center.name,
    description: center.description,
    contact_email: center.contact_email,
    contact_phone: center.contact_phone,
  };

  async function handleSubmit(values: CenterFormValues) {
    await updateCenter.mutateAsync(
      { id: centerId, payload: values },
      {
        onSuccess: () => {
          toast.success("Centro de investigación actualizado.");
          router.push(`/institutions/${id}/centers/${centerId}`);
        },
        onError: (error) => {
          toast.error(getErrorMessage(error));
        },
      },
    );
  }

  return (
    <AuthenticatedLayout>
      <h1 className="mb-6 text-2xl font-semibold">Editar centro de investigación</h1>

      <RoleGuard allowedRoles={centerConfig.minRoles}>
        <Card>
          <CardContent className="p-6">
            <EntityForm<CenterFormValues>
              config={centerConfig}
              defaultValues={defaultValues}
              submitLabel="Guardar cambios"
              onSubmit={handleSubmit}
              onError={(error) => toast.error(getErrorMessage(error))}
              fieldOptions={{ sede: sedeOptions, facultad: facultadOptions }}
            />
          </CardContent>
        </Card>
      </RoleGuard>
    </AuthenticatedLayout>
  );
}