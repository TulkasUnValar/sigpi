"use client";

/**
 * Sede edit — generic EntityForm prefilled from the detail; PATCH
 * /api/sedes/{id}/. Parent ids never appear in the body.
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
import { sedeConfig, type SedeFormValues } from "@/features/institutions/schemas";
import { useSedeDetail } from "@/features/institutions/queries";
import { useUpdateSede } from "@/features/institutions/mutations";

export default function EditSedePage() {
  const params = useParams<{ id: string; sedeId: string }>();
  const { id, sedeId } = params;
  const router = useRouter();

  const detailQuery = useSedeDetail(sedeId);
  const updateSede = useUpdateSede();

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

  const defaultValues: SedeFormValues = {
    code: sede.code,
    name: sede.name,
    description: sede.description,
  };

  async function handleSubmit(values: SedeFormValues) {
    await updateSede.mutateAsync(
      { id: sedeId, payload: values },
      {
        onSuccess: () => {
          toast.success("Sede actualizada.");
          router.push(`/institutions/${id}/sedes/${sedeId}`);
        },
        onError: (error) => {
          toast.error(getErrorMessage(error));
        },
      },
    );
  }

  return (
    <AuthenticatedLayout>
      <h1 className="mb-6 text-2xl font-semibold">Editar sede</h1>

      <RoleGuard allowedRoles={sedeConfig.minRoles}>
        <Card>
          <CardContent className="p-6">
            <EntityForm<SedeFormValues>
              config={sedeConfig}
              defaultValues={defaultValues}
              submitLabel="Guardar cambios"
              onSubmit={handleSubmit}
              onError={(error) => toast.error(getErrorMessage(error))}
            />
          </CardContent>
        </Card>
      </RoleGuard>
    </AuthenticatedLayout>
  );
}