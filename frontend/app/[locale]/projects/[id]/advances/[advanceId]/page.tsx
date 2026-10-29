"use client";

/**
 * Advance detail — /projects/[id]/advances/[advanceId].
 *
 * RF-046: thin route adapter over the extracted AdvanceDetail component.
 */

import { useParams } from "next/navigation";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { useAuthStore } from "@/store/auth";
import { AdvanceDetail, useAdvanceDetail } from "@/features/advances";

export default function AdvanceDetailPage() {
  const params = useParams<{ id: string; advanceId: string }>();
  const projectId = params.id;
  const advanceId = params.advanceId;

  const userId = useAuthStore((s) => s.user?.id);
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

  return (
    <AuthenticatedLayout>
      <AdvanceDetail
        advance={advance}
        advanceId={advanceId}
        projectId={projectId}
        userId={userId ?? null}
      />
    </AuthenticatedLayout>
  );
}
