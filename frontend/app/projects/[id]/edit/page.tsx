"use client";

/**
 * Edit project page — /projects/[id]/edit (FR-05 / FR-06 / FR-07).
 *
 * Spec (projects-ui edit): renders the shared ProjectForm seeded from
 * `useProjectDetail`; the form PATCHes the writable scalars and redirects
 * to the detail on success. A terminal project (RN-011) is not editable
 * for non-admins, so the route refuses to render the form and keeps the
 * user in-page; the backend 403 remains the authorization backstop.
 */

import Link from "next/link";
import { useParams } from "next/navigation";

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { Skeleton } from "@/components/shared/Skeleton";
import { EmptyState } from "@/components/shared/EmptyState";
import { useAuthStore } from "@/store/auth";
import { ProjectForm, canEditProject, useProjectDetail } from "@/features/projects";

export default function EditProjectPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const roles = useAuthStore((s) => s.roles);

  const detailQuery = useProjectDetail(id);

  if (detailQuery.isLoading) {
    return (
      <AuthenticatedLayout>
        <Skeleton className="mb-4 h-8 w-64" />
        <Skeleton className="h-64" />
      </AuthenticatedLayout>
    );
  }

  const project = detailQuery.data;
  if (!project) {
    return (
      <AuthenticatedLayout>
        <EmptyState title="Proyecto no encontrado" />
      </AuthenticatedLayout>
    );
  }

  if (!canEditProject(project.status, roles)) {
    return (
      <AuthenticatedLayout>
        <EmptyState
          title="Este proyecto no se puede editar"
          description="Los proyectos cerrados, rechazados o cancelados no son editables."
        />
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <div className="mb-6">
        <Link href={`/projects/${id}`} className="text-sm text-muted-foreground hover:underline">
          ← Volver al proyecto
        </Link>
      </div>
      <ProjectForm project={project} />
    </AuthenticatedLayout>
  );
}
