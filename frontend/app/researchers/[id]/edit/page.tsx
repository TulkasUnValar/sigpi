"use client";

/**
 * Researcher edit — prefilled form with is_active reactivation toggle.
 *
 * Spec (researchers-ui edit):
 *   - PATCH /api/researchers/{id}/ is allowed for the linked self or
 *     admin+ (gated on the detail `user`).
 *   - The `is_active` switch enables reactivation (no activate endpoint
 *     exists; reactivation is a PATCH with is_active:true).
 *   - Success redirects to the detail route.
 */

import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { getErrorMessage } from "@/lib/errors";
import { useAuthStore } from "@/store/auth";
import { ResearcherForm } from "@/features/researchers/ResearcherForm";
import { useResearcherDetail } from "@/features/researchers/queries";
import { useUpdateResearcher } from "@/features/researchers/mutations";
import { canEditResearcher } from "@/features/researchers/permissions";
import type { ResearcherCreateFormValues } from "@/features/researchers/schemas";

export default function EditResearcherPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();

  const { user, roles } = useAuthStore();
  const detailQuery = useResearcherDetail(id);
  const updateResearcher = useUpdateResearcher(id);

  if (detailQuery.isLoading) {
    return (
      <AuthenticatedLayout>
        <Skeleton className="mb-4 h-8 w-64" />
        <Skeleton className="h-64" />
      </AuthenticatedLayout>
    );
  }

  const researcher = detailQuery.data;
  if (!researcher) {
    return (
      <AuthenticatedLayout>
        <EmptyState title="Investigador no encontrado" />
      </AuthenticatedLayout>
    );
  }

  if (!canEditResearcher(researcher, user?.id ?? null, roles)) {
    return (
      <AuthenticatedLayout>
        <EmptyState title="No tiene permisos para editar este investigador." />
      </AuthenticatedLayout>
    );
  }

  const defaultValues: ResearcherCreateFormValues = {
    first_name: researcher.first_name,
    last_name: researcher.last_name,
    document_type: researcher.document_type as ResearcherCreateFormValues["document_type"],
    document_number: researcher.document_number,
    primary_email: researcher.primary_email,
    phone: researcher.phone,
    bio: researcher.bio,
    academic_formation: researcher.academic_formation,
    is_active: researcher.is_active,
  };

  async function handleSubmit(values: ResearcherCreateFormValues) {
    await updateResearcher.mutateAsync(values, {
      onSuccess: () => {
        toast.success("Investigador actualizado.");
        router.push(`/researchers/${id}`);
      },
      onError: (error) => {
        toast.error(getErrorMessage(error));
      },
    });
  }

  return (
    <AuthenticatedLayout>
      <h1 className="mb-6 text-2xl font-semibold">Editar investigador</h1>

      <Card>
        <CardContent className="p-6">
          <ResearcherForm
            defaultValues={defaultValues}
            submitLabel="Guardar cambios"
            onSubmit={handleSubmit}
            onError={(error) => toast.error(getErrorMessage(error))}
          />
        </CardContent>
      </Card>
    </AuthenticatedLayout>
  );
}
