"use client";

/**
 * Advance edit — /projects/[id]/advances/[advanceId]/edit.
 *
 * Spec (RF-043):
 *   Renders the shared AdvanceForm seeded from the detail query, PATCHing
 *   only writable fields with `project` omitted. Edit access is gated to
 *   advances in `borrador`; the backend 403 remains the authorization
 *   backstop.
 */

import Link from "next/link";
import { useParams } from "next/navigation";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { AdvanceForm, useAdvanceDetail } from "@/features/advances";

export default function EditAdvancePage() {
  const params = useParams<{ id: string; advanceId: string }>();
  const projectId = params.id;
  const advanceId = params.advanceId;

  const detailQuery = useAdvanceDetail(advanceId);

  if (detailQuery.isLoading) {
    return (
      <AuthenticatedLayout>
        <Skeleton className="mb-4 h-8 w-64" />
        <Skeleton className="h-64" />
      </AuthenticatedLayout>
    );
  }

  const advance = detailQuery.data;
  if (!advance) {
    return (
      <AuthenticatedLayout>
        <EmptyState title="Avance no encontrado" />
      </AuthenticatedLayout>
    );
  }

  if (advance.status !== "borrador") {
    return (
      <AuthenticatedLayout>
        <EmptyState
          title="Este avance no se puede editar"
          description="Solo los avances en borrador son editables."
        />
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <div className="mb-6">
        <Link
          href={`/projects/${projectId}/advances/${advanceId}`}
          className="text-sm text-muted-foreground hover:underline"
        >
          ← Volver al avance
        </Link>
      </div>
      <AdvanceForm advance={advance} projectId={projectId} />
    </AuthenticatedLayout>
  );
}
