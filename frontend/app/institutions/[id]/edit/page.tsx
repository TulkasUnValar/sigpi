"use client";

/**
 * Institution edit — generic EntityForm prefilled from the detail.
 *
 * Spec (institutions-ui RF-F02):
 *   - PATCH /api/institutions/{id}/ updates the root institution.
 *   - 400 field errors map back into the form; the detail refetches
 *     after success (mutation invalidates the institutions cache).
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
import { institutionConfig } from "@/features/institutions/schemas";
import { useInstitutionDetail } from "@/features/institutions/queries";
import { useUpdateInstitution } from "@/features/institutions/mutations";
import type { InstitutionFormValues } from "@/features/institutions/schemas";

export default function EditInstitutionPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();

  const detailQuery = useInstitutionDetail(id);
  const updateInstitution = useUpdateInstitution(id);

  if (detailQuery.isLoading) {
    return (
      <AuthenticatedLayout>
        <Skeleton className="mb-4 h-8 w-64" />
        <Skeleton className="h-64" />
      </AuthenticatedLayout>
    );
  }

  const institution = detailQuery.data;
  if (!institution) {
    return (
      <AuthenticatedLayout>
        <EmptyState title="Institución no encontrada" />
      </AuthenticatedLayout>
    );
  }

  const defaultValues: InstitutionFormValues = {
    name: institution.name,
    code: institution.code,
    description: institution.description,
    address: institution.address,
    contact_email: institution.contact_email,
    contact_phone: institution.contact_phone,
    logo_url: institution.logo_url,
  };

  async function handleSubmit(values: InstitutionFormValues) {
    await updateInstitution.mutateAsync(values, {
      onSuccess: () => {
        toast.success("Institución actualizada.");
        router.push(`/institutions/${id}`);
      },
      onError: (error) => {
        toast.error(getErrorMessage(error));
      },
    });
  }

  return (
    <AuthenticatedLayout>
      <h1 className="mb-6 text-2xl font-semibold">Editar institución</h1>

      <RoleGuard allowedRoles={institutionConfig.minRoles}>
        <Card>
          <CardContent className="p-6">
            <EntityForm<InstitutionFormValues>
              config={institutionConfig}
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
