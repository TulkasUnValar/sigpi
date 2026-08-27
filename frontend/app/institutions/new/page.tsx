"use client";

/**
 * Institution create — generic EntityForm (RHF + zod).
 *
 * Spec (institutions-ui RF-F02):
 *   - Superadmin creates an institution → POST /api/institutions/ succeeds
 *     and the tree refetches (mutation invalidates the institutions cache).
 *   - 400 field errors map back into the form; 409 duplicate-code detail
 *     surfaces via Toaster and the form keeps its values.
 */

import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Card, CardContent } from "@/components/ui/card";
import { RoleGuard } from "@/components/shell/RoleGuard";
import { getErrorMessage } from "@/lib/errors";
import { EntityForm } from "@/features/institutions/EntityForm";
import { institutionConfig } from "@/features/institutions/schemas";
import { useCreateInstitution } from "@/features/institutions/mutations";
import type { InstitutionFormValues } from "@/features/institutions/schemas";

const DEFAULT_VALUES: InstitutionFormValues = {
  name: "",
  code: "",
  description: "",
  address: "",
  contact_email: "",
  contact_phone: "",
  logo_url: "",
};

export default function NewInstitutionPage() {
  const router = useRouter();
  const createInstitution = useCreateInstitution();

  async function handleSubmit(values: InstitutionFormValues) {
    await createInstitution.mutateAsync(values, {
      onSuccess: (institution) => {
        toast.success("Institución creada.");
        router.push(`/institutions/${institution.id}`);
      },
      onError: (error) => {
        toast.error(getErrorMessage(error));
      },
    });
  }

  return (
    <AuthenticatedLayout>
      <h1 className="mb-6 text-2xl font-semibold">Nueva institución</h1>

      <RoleGuard allowedRoles={institutionConfig.minRoles}>
        <Card>
          <CardContent className="p-6">
            <EntityForm<InstitutionFormValues>
              config={institutionConfig}
              defaultValues={DEFAULT_VALUES}
              submitLabel="Crear institución"
              onSubmit={handleSubmit}
              onError={(error) => toast.error(getErrorMessage(error))}
            />
          </CardContent>
        </Card>
      </RoleGuard>
    </AuthenticatedLayout>
  );
}
