"use client";

/**
 * Facultad create — generic EntityForm with an optional sede reference.
 *
 * Spec (institutions-ui RF-F03/RF-F05):
 *   - POST /api/institutions/{pk}/facultades/ — the parent (institution)
 *     comes from the URL; `sede` is an optional reference field.
 *   - Write threshold: admin or superadmin (RoleGuard).
 */

import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Card, CardContent } from "@/components/ui/card";
import { RoleGuard } from "@/components/shell/RoleGuard";
import { getErrorMessage } from "@/lib/errors";
import { EntityForm } from "@/features/institutions/EntityForm";
import { facultadConfig, type FacultadFormValues } from "@/features/institutions/schemas";
import { useSedes } from "@/features/institutions/queries";
import { useCreateFacultad } from "@/features/institutions/mutations";
import type { EntityFieldOption } from "@/features/institutions/types";

const DEFAULT_VALUES: FacultadFormValues = {
  sede: "",
  code: "",
  name: "",
  description: "",
};

export default function NewFacultadPage() {
  const params = useParams<{ id: string }>();
  const instId = params.id;
  const router = useRouter();

  const createFacultad = useCreateFacultad(instId);
  const sedesQuery = useSedes(instId);
  const sedeOptions: EntityFieldOption[] = (sedesQuery.data?.results ?? []).map((sede) => ({
    value: sede.id,
    label: sede.name,
  }));

  async function handleSubmit(values: FacultadFormValues) {
    await createFacultad.mutateAsync(values, {
      onSuccess: (facultad) => {
        toast.success("Facultad creada.");
        router.push(`/institutions/${instId}/facultades/${facultad.id}`);
      },
      onError: (error) => {
        toast.error(getErrorMessage(error));
      },
    });
  }

  return (
    <AuthenticatedLayout>
      <h1 className="mb-6 text-2xl font-semibold">Nueva facultad</h1>

      <RoleGuard allowedRoles={facultadConfig.minRoles}>
        <Card>
          <CardContent className="p-6">
            <EntityForm<FacultadFormValues>
              config={facultadConfig}
              defaultValues={DEFAULT_VALUES}
              submitLabel="Crear facultad"
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