"use client";

/**
 * Call detail page — thin App Router composition over CallDetail.
 *
 * Spec (calls-ui detail): /calls/{id} renders the header, FSM action bar
 * and the four tabs with Overview data.
 */

import { useParams } from "next/navigation";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { CallDetail } from "@/features/calls/CallDetail";
import { useCallDetail } from "@/features/calls/queries";

export default function CallDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const detailQuery = useCallDetail(id);

  if (detailQuery.isLoading) {
    return (
      <AuthenticatedLayout>
        <Skeleton className="mb-4 h-8 w-64" />
        <Skeleton className="h-64" />
      </AuthenticatedLayout>
    );
  }

  const call = detailQuery.data;
  if (!call) {
    return (
      <AuthenticatedLayout>
        <EmptyState title="Convocatoria no encontrada" />
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <CallDetail call={call} />
    </AuthenticatedLayout>
  );
}