"use client";

/**
 * Facultad edit — generic EntityForm prefilled from the detail; PATCH
 * /api/facultades/{id}/. The optional sede reference is selectable.
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
import { facultadConfig, type FacultadFormValues } from "@/features/institutions/schemas";
import { useFacultadDetail, useSedes } from "@/features/institutions/queries";
import { useUpdateFacultad } from "@/features/institutions/mutations";
import type { EntityFieldOption } from "@/features/institutions/types";

export default function EditFacultadPage() {
  const params = useParams<{ id: string; facultadId: string }>();
  const { id, facultadId } = params;
  const router = useRouter();

  const detailQuery = useFacultadDetail(facultadId);
  const updateFacultad = useUpdateFacultad();
  const sedesQuery = useSedes(id);
  const sedeOptions: EntityFieldOption[] = (sedesQuery.data?.results ?? []).map((sede) => ({
    value: sede.id,
    label: sede.name,
  }));

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

  const defaultValues: FacultadFormValues = {
    sede: facultad.sede ?? "",
    code: facultad.code,
    name: facultad.name,
    description: facultad.description,
  };

  async function handleSubmit(values: FacultadFormValues) {
    await updateFacultad.mutateAsync(
      { id: facultadId, payload: values },
      {
        onSuccess: () => {
          toast.success("Facultad actualizada.");
          router.push(`/institutions/${id}/facultades/${facultadId}`);
        },
        onError: (error) => {
          toast.error(getErrorMessage(error));
        },
      },
    );
  }

  return (
    <AuthenticatedLayout>
      <h1 className="mb-6 text-2xl font-semibold">Editar facultad</h1>

      <RoleGuard allowedRoles={facultadConfig.minRoles}>
        <Card>
          <CardContent className="p-6">
            <EntityForm<FacultadFormValues>
              config={facultadConfig}
              defaultValues={defaultValues}
              submitLabel="Guardar cambios"
              onSubmit={handleSubmit}
              onError={(error) => toast.error(getErrorMessage(error))}
              fieldOptions={{ sede: sedeOptions }}
            />
          </CardContent>
        </Card>
      </RoleGuard>
    </AuthenticatedLayout>
  );
}