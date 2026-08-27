"use client";

/**
 * Center create — generic EntityForm with sede/facultad references.
 *
 * Spec (institutions-ui RF-F03/RF-F05):
 *   - POST /api/institutions/{pk}/centers/ — the parent (institution)
 *     comes from the URL; parent_type may be institution | sede | facultad
 *     selected through the optional sede/facultad references.
 *   - Write threshold: admin or superadmin (RoleGuard).
 */

import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Card, CardContent } from "@/components/ui/card";
import { RoleGuard } from "@/components/shell/RoleGuard";
import { getErrorMessage } from "@/lib/errors";
import { EntityForm } from "@/features/institutions/EntityForm";
import { centerConfig, type CenterFormValues } from "@/features/institutions/schemas";
import { useFacultades, useSedes } from "@/features/institutions/queries";
import { useCreateCenter } from "@/features/institutions/mutations";
import type { EntityFieldOption } from "@/features/institutions/types";

const DEFAULT_VALUES: CenterFormValues = {
  sede: "",
  facultad: "",
  code: "",
  name: "",
  description: "",
  contact_email: "",
  contact_phone: "",
};

export default function NewCenterPage() {
  const params = useParams<{ id: string }>();
  const instId = params.id;
  const router = useRouter();

  const createCenter = useCreateCenter(instId);
  const sedesQuery = useSedes(instId);
  const facultadesQuery = useFacultades(instId);

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

  async function handleSubmit(values: CenterFormValues) {
    await createCenter.mutateAsync(values, {
      onSuccess: (center) => {
        toast.success("Centro de investigación creado.");
        router.push(`/institutions/${instId}/centers/${center.id}`);
      },
      onError: (error) => {
        toast.error(getErrorMessage(error));
      },
    });
  }

  return (
    <AuthenticatedLayout>
      <h1 className="mb-6 text-2xl font-semibold">Nuevo centro de investigación</h1>

      <RoleGuard allowedRoles={centerConfig.minRoles}>
        <Card>
          <CardContent className="p-6">
            <EntityForm<CenterFormValues>
              config={centerConfig}
              defaultValues={DEFAULT_VALUES}
              submitLabel="Crear centro de investigación"
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