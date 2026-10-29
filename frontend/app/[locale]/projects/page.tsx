"use client";

/**
 * Projects list route — thin App Router composition over ProjectList.
 *
 * Spec (projects-ui list / FR-02): /projects renders the paginated
 * projects list inside the authenticated shell. The list UI lives in
 * `features/projects/ProjectList.tsx`.
 */

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { ProjectList } from "@/features/projects";

export default function ProjectsPage() {
  return (
    <AuthenticatedLayout>
      <ProjectList />
    </AuthenticatedLayout>
  );
}
