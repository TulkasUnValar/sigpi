"use client";

/**
 * Line edit — generic EntityForm prefilled from the detail; PATCH
 * /api/lines/{id}/. Write threshold: director/admin/superadmin (RF-F05).
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
import { lineConfig, type LineFormValues } from "@/features/institutions/schemas";
import { useResearchLineDetail } from "@/features/institutions/queries";
import { useUpdateResearchLine } from "@/features/institutions/mutations";

export default function EditLinePage() {
  const params = useParams<{ id: string; centerId: string; groupId: string; lineId: string }>();
  const { id, centerId, groupId, lineId } = params;
  const router = useRouter();

  const detailQuery = useResearchLineDetail(lineId);
  const updateLine = useUpdateResearchLine();

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

  const defaultValues: LineFormValues = {
    code: line.code,
    name: line.name,
    description: line.description,
  };

  async function handleSubmit(values: LineFormValues) {
    await updateLine.mutateAsync(
      { id: lineId, payload: values },
      {
        onSuccess: () => {
          toast.success("Línea de investigación actualizada.");
          router.push(`/institutions/${id}/centers/${centerId}/groups/${groupId}/lines/${lineId}`);
        },
        onError: (error) => {
          toast.error(getErrorMessage(error));
        },
      },
    );
  }

  return (
    <AuthenticatedLayout>
      <h1 className="mb-6 text-2xl font-semibold">Editar línea de investigación</h1>

      <RoleGuard allowedRoles={lineConfig.minRoles}>
        <Card>
          <CardContent className="p-6">
            <EntityForm<LineFormValues>
              config={lineConfig}
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
