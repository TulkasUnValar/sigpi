"use client";

/**
 * Project detail route — thin App Router composition over ProjectDetail.
 *
 * Spec (projects-ui detail / FR-02): /projects/[id] renders the detail
 * tabs, FSM action bar, and StatusBadge inside the authenticated shell.
 * The detail UI lives in `features/projects/ProjectDetail.tsx`.
 */

import { useParams } from "next/navigation";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { ProjectDetail } from "@/features/projects";

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();

  return (
    <AuthenticatedLayout>
      <ProjectDetail id={params.id} />
    </AuthenticatedLayout>
  );
}
