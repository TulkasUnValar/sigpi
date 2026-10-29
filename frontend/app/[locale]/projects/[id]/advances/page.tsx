"use client";

/**
 * Advances nested list — /projects/[id]/advances.
 *
 * RF-046: thin route adapter over the extracted AdvanceList component.
 */

import Link from "next/link";
import { useParams } from "next/navigation";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Button } from "@/components/ui/button";
import { AdvanceList, useAdvancesList } from "@/features/advances";

export default function AdvancesPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;

  const advancesQuery = useAdvancesList(projectId);
  const advances = advancesQuery.data?.results ?? [];

  return (
    <AuthenticatedLayout>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <Link
            href={`/projects/${projectId}`}
            className="text-sm text-muted-foreground hover:underline"
          >
            ← Volver al proyecto
          </Link>
          <h1 className="mt-1 text-2xl font-semibold">Avances</h1>
        </div>
        <Button asChild>
          <Link href={`/projects/${projectId}/advances/new`}>Nuevo avance</Link>
        </Button>
      </div>

      <AdvanceList advances={advances} isLoading={advancesQuery.isLoading} projectId={projectId} />
    </AuthenticatedLayout>
  );
}
