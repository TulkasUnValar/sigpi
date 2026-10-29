"use client";

/**
 * Advance create — /projects/[id]/advances/new.
 *
 * Spec (advances-ui create & FSM):
 *   Thin route adapter over the shared AdvanceForm; the form defaults the
 *   project select to this route's project and redirects to the advances
 *   list after POST /api/progress/ succeeds.
 */

import { useParams } from "next/navigation";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { AdvanceForm } from "@/features/advances";

export default function NewAdvancePage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;

  return (
    <AuthenticatedLayout>
      <AdvanceForm projectId={projectId} />
    </AuthenticatedLayout>
  );
}
