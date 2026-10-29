"use client";

/**
 * Group create — generic EntityForm for a research group (RF-F03).
 *
 * POST /api/centers/{centerId}/groups/ — the parent (center) comes from
 * the URL, never from the body. Write threshold: director/admin/superadmin.
 */

import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Card, CardContent } from "@/components/ui/card";
import { RoleGuard } from "@/components/shell/RoleGuard";
import { getErrorMessage } from "@/lib/errors";
import { EntityForm } from "@/features/institutions/EntityForm";
import { groupConfig, type GroupFormValues } from "@/features/institutions/schemas";
import { useCreateResearchGroup } from "@/features/institutions/mutations";

const DEFAULT_VALUES: GroupFormValues = {
  code: "",
  name: "",
  description: "",
};

export default function NewGroupPage() {
  const params = useParams<{ id: string; centerId: string }>();
  const { id, centerId } = params;
  const router = useRouter();

  const createGroup = useCreateResearchGroup(centerId);

  async function handleSubmit(values: GroupFormValues) {
    await createGroup.mutateAsync(values, {
      onSuccess: (group) => {
        toast.success("Grupo de investigación creado.");
        router.push(`/institutions/${id}/centers/${centerId}/groups/${group.id}`);
      },
      onError: (error) => {
        toast.error(getErrorMessage(error));
      },
    });
  }

  return (
    <AuthenticatedLayout>
      <h1 className="mb-6 text-2xl font-semibold">Nuevo grupo de investigación</h1>

      <RoleGuard allowedRoles={groupConfig.minRoles}>
        <Card>
          <CardContent className="p-6">
            <EntityForm<GroupFormValues>
              config={groupConfig}
              defaultValues={DEFAULT_VALUES}
              submitLabel="Crear grupo de investigación"
              onSubmit={handleSubmit}
              onError={(error) => toast.error(getErrorMessage(error))}
            />
          </CardContent>
        </Card>
      </RoleGuard>
    </AuthenticatedLayout>
  );
}
