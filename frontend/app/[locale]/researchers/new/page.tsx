"use client";

/**
 * Researcher create — role-gated form.
 *
 * Spec (researchers-ui create):
 *   - Create is director+ (level ≤ 3): director, admin, superadmin.
 *   - POST /api/researchers/ succeeds → redirect to /researchers/{id}.
 *   - Duplicate-document 400 maps into the form (no redirect); other
 *     errors surface via Toaster.
 */

import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Card, CardContent } from "@/components/ui/card";
import { RoleGuard } from "@/components/shell/RoleGuard";
import { getErrorMessage } from "@/lib/errors";
import { ResearcherForm } from "@/features/researchers/ResearcherForm";
import { useCreateResearcher } from "@/features/researchers/mutations";
import type { ResearcherCreateFormValues } from "@/features/researchers/schemas";

/** Roles allowed to create researchers (director+, level ≤ 3). */
const CREATE_ROLES = ["director", "admin", "superadmin"];

const DEFAULT_VALUES: ResearcherCreateFormValues = {
  first_name: "",
  last_name: "",
  document_type: "CC",
  document_number: "",
  primary_email: "",
  phone: "",
  bio: "",
  academic_formation: "",
  is_active: true,
};

export default function NewResearcherPage() {
  const router = useRouter();
  const createResearcher = useCreateResearcher();

  async function handleSubmit(values: ResearcherCreateFormValues) {
    await createResearcher.mutateAsync(values, {
      onSuccess: (researcher) => {
        toast.success("Investigador creado.");
        router.push(`/researchers/${researcher.id}`);
      },
      onError: (error) => {
        toast.error(getErrorMessage(error));
      },
    });
  }

  return (
    <AuthenticatedLayout>
      <h1 className="mb-6 text-2xl font-semibold">Nuevo investigador</h1>

      <RoleGuard allowedRoles={CREATE_ROLES}>
        <Card>
          <CardContent className="p-6">
            <ResearcherForm
              defaultValues={DEFAULT_VALUES}
              submitLabel="Crear investigador"
              onSubmit={handleSubmit}
              onError={(error) => toast.error(getErrorMessage(error))}
            />
          </CardContent>
        </Card>
      </RoleGuard>
    </AuthenticatedLayout>
  );
}
