"use client";

/**
 * Sede create — generic EntityForm; parent institution from URL params.
 *
 * Spec (institutions-ui RF-F03/RF-F05):
 *   - POST /api/institutions/{pk}/sedes/ — the parent is NEVER in the body.
 *   - Write threshold: admin or superadmin (RoleGuard).
 */

import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Card, CardContent } from "@/components/ui/card";
import { RoleGuard } from "@/components/shell/RoleGuard";
import { getErrorMessage } from "@/lib/errors";
import { EntityForm } from "@/features/institutions/EntityForm";
import { sedeConfig, type SedeFormValues } from "@/features/institutions/schemas";
import { useCreateSede } from "@/features/institutions/mutations";

const DEFAULT_VALUES: SedeFormValues = {
  code: "",
  name: "",
  description: "",
};

export default function NewSedePage() {
  const params = useParams<{ id: string }>();
  const instId = params.id;
  const router = useRouter();
  const createSede = useCreateSede(instId);

  async function handleSubmit(values: SedeFormValues) {
    await createSede.mutateAsync(values, {
      onSuccess: (sede) => {
        toast.success("Sede creada.");
        router.push(`/institutions/${instId}/sedes/${sede.id}`);
      },
      onError: (error) => {
        toast.error(getErrorMessage(error));
      },
    });
  }

  return (
    <AuthenticatedLayout>
      <h1 className="mb-6 text-2xl font-semibold">Nueva sede</h1>

      <RoleGuard allowedRoles={sedeConfig.minRoles}>
        <Card>
          <CardContent className="p-6">
            <EntityForm<SedeFormValues>
              config={sedeConfig}
              defaultValues={DEFAULT_VALUES}
              submitLabel="Crear sede"
              onSubmit={handleSubmit}
              onError={(error) => toast.error(getErrorMessage(error))}
            />
          </CardContent>
        </Card>
      </RoleGuard>
    </AuthenticatedLayout>
  );
}