"use client";

/**
 * Line create — generic EntityForm for a research line (RF-F03).
 *
 * POST /api/groups/{groupId}/lines/ — the parent (group) comes from the
 * URL, never from the body. Write threshold: director/admin/superadmin.
 */

import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Card, CardContent } from "@/components/ui/card";
import { RoleGuard } from "@/components/shell/RoleGuard";
import { getErrorMessage } from "@/lib/errors";
import { EntityForm } from "@/features/institutions/EntityForm";
import { lineConfig, type LineFormValues } from "@/features/institutions/schemas";
import { useCreateResearchLine } from "@/features/institutions/mutations";

const DEFAULT_VALUES: LineFormValues = {
  code: "",
  name: "",
  description: "",
};

export default function NewLinePage() {
  const params = useParams<{ id: string; centerId: string; groupId: string }>();
  const { id, centerId, groupId } = params;
  const router = useRouter();

  const createLine = useCreateResearchLine(groupId);

  async function handleSubmit(values: LineFormValues) {
    await createLine.mutateAsync(values, {
      onSuccess: (line) => {
        toast.success("Línea de investigación creada.");
        router.push(`/institutions/${id}/centers/${centerId}/groups/${groupId}/lines/${line.id}`);
      },
      onError: (error) => {
        toast.error(getErrorMessage(error));
      },
    });
  }

  return (
    <AuthenticatedLayout>
      <h1 className="mb-6 text-2xl font-semibold">Nueva línea de investigación</h1>

      <RoleGuard allowedRoles={lineConfig.minRoles}>
        <Card>
          <CardContent className="p-6">
            <EntityForm<LineFormValues>
              config={lineConfig}
              defaultValues={DEFAULT_VALUES}
              submitLabel="Crear línea de investigación"
              onSubmit={handleSubmit}
              onError={(error) => toast.error(getErrorMessage(error))}
            />
          </CardContent>
        </Card>
      </RoleGuard>
    </AuthenticatedLayout>
  );
}
