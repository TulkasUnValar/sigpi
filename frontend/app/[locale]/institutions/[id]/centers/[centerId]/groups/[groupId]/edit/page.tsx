"use client";

/**
 * Group edit — generic EntityForm prefilled from the detail; PATCH
 * /api/groups/{id}/. Write threshold: director/admin/superadmin (RF-F05).
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
import { groupConfig, type GroupFormValues } from "@/features/institutions/schemas";
import { useResearchGroupDetail } from "@/features/institutions/queries";
import { useUpdateResearchGroup } from "@/features/institutions/mutations";

export default function EditGroupPage() {
  const params = useParams<{ id: string; centerId: string; groupId: string }>();
  const { id, centerId, groupId } = params;
  const router = useRouter();

  const detailQuery = useResearchGroupDetail(groupId);
  const updateGroup = useUpdateResearchGroup();

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

  const defaultValues: GroupFormValues = {
    code: group.code,
    name: group.name,
    description: group.description,
  };

  async function handleSubmit(values: GroupFormValues) {
    await updateGroup.mutateAsync(
      { id: groupId, payload: values },
      {
        onSuccess: () => {
          toast.success("Grupo de investigación actualizado.");
          router.push(`/institutions/${id}/centers/${centerId}/groups/${groupId}`);
        },
        onError: (error) => {
          toast.error(getErrorMessage(error));
        },
      },
    );
  }

  return (
    <AuthenticatedLayout>
      <h1 className="mb-6 text-2xl font-semibold">Editar grupo de investigación</h1>

      <RoleGuard allowedRoles={groupConfig.minRoles}>
        <Card>
          <CardContent className="p-6">
            <EntityForm<GroupFormValues>
              config={groupConfig}
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
