"use client";

/**
 * Projects create route — thin App Router composition over ProjectWizard.
 *
 * Spec (projects-ui create wizard / FR-03): /projects/new renders the
 * multi-step create wizard inside the authenticated shell. The wizard UI
 * lives in `features/projects/ProjectWizard.tsx`.
 */

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { ProjectWizard } from "@/features/projects";

export default function NewProjectPage() {
  return (
    <AuthenticatedLayout>
      <ProjectWizard />
    </AuthenticatedLayout>
  );
}
