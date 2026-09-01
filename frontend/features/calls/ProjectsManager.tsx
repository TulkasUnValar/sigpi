"use client";

/**
 * ProjectsManager — link/unlink projects to a call.
 *
 * Spec (calls-ui projects):
 *   - Lists the linked projects (GET /calls/{id}/projects/).
 *   - Linking is offered ONLY when the call is `abierta`.
 *   - A duplicate association (409) surfaces its detail via the Toaster.
 *   - Unlink is destructive and confirms before DELETE.
 */

import { useState } from "react";
import { toast } from "sonner";
import { Link2, Unlink } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { EmptyState } from "@/components/shared/EmptyState";
import { getErrorMessage } from "@/lib/errors";
import { useAuthStore } from "@/store/auth";
import { canManageCall } from "@/features/calls/permissions";
import { useCallProjects, useProjectOptions } from "@/features/calls/queries";
import { useLinkProject, useUnlinkProject } from "@/features/calls/mutations";
import type { CallProject } from "@/features/calls/types";

interface ProjectsManagerProps {
  callId: string;
  status: string;
}

export function ProjectsManager({ callId, status }: ProjectsManagerProps) {
  const roles = useAuthStore((s) => s.roles);
  const canEdit = canManageCall(roles);
  const isOpen = status === "abierta";

  const projectsQuery = useCallProjects(callId);
  const optionsQuery = useProjectOptions();
  const linkProject = useLinkProject();
  const unlinkProject = useUnlinkProject();

  const [selectedProject, setSelectedProject] = useState<string>("");
  const [unlinking, setUnlinking] = useState<CallProject | null>(null);

  const linked = projectsQuery.data?.results ?? [];
  const options = optionsQuery.data?.results ?? [];
  const linkedIds = new Set(linked.map((cp) => cp.project));
  const linkable = options.filter((p) => !linkedIds.has(p.id));

  const titleById = new Map(options.map((p) => [p.id, p.title]));

  function handleLink() {
    if (!selectedProject) return;
    linkProject.mutate(
      { callId, project: selectedProject },
      {
        onSuccess: () => {
          toast.success("Proyecto vinculado.");
          setSelectedProject("");
        },
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  }

  function handleUnlink(cp: CallProject) {
    unlinkProject.mutate(
      { callId, projectId: cp.id },
      {
        onSuccess: () => toast.success("Proyecto desvinculado."),
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  }

  const pending = linkProject.isPending || unlinkProject.isPending;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Proyectos vinculados</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4">
        {linked.length === 0 ? (
          <EmptyState
            title="Sin proyectos"
            description="Todavía no hay proyectos vinculados a esta convocatoria."
          />
        ) : (
          <ul className="grid gap-3">
            {linked.map((cp) => (
              <li
                key={cp.id}
                className="flex items-center justify-between gap-3 rounded-lg border p-3"
              >
                <div className="min-w-0">
                  <p className="font-medium">{titleById.get(cp.project) ?? cp.project}</p>
                  <p className="text-sm text-muted-foreground">Vinculado: {cp.linked_at}</p>
                </div>
                {canEdit ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    aria-label={`Desvincular proyecto ${titleById.get(cp.project) ?? cp.project}`}
                    onClick={() => setUnlinking(cp)}
                    disabled={pending}
                  >
                    <Unlink className="h-4 w-4" />
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        )}

        {canEdit && isOpen ? (
          <div className="flex flex-wrap items-end gap-3 rounded-lg border p-3">
            <div className="min-w-56 flex-1">
              <Label htmlFor="project-to-link">Proyecto a vincular</Label>
              <select
                id="project-to-link"
                value={selectedProject}
                onChange={(e) => setSelectedProject(e.target.value)}
                className="mt-1 flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                <option value="">Selecciona un proyecto</option>
                {linkable.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title}
                  </option>
                ))}
              </select>
            </div>
            <Button size="sm" onClick={handleLink} disabled={pending || !selectedProject}>
              <Link2 className="mr-1 h-4 w-4" />
              Vincular
            </Button>
          </div>
        ) : null}
      </CardContent>

      {unlinking ? (
        <ConfirmDialog
          open={Boolean(unlinking)}
          onOpenChange={(open) => {
            if (!open) setUnlinking(null);
          }}
          title="¿Desvincular proyecto?"
          description="El proyecto dejará de estar asociado a esta convocatoria."
          confirmLabel="Desvincular"
          cancelLabel="Cancelar"
          destructive
          onConfirm={() => handleUnlink(unlinking)}
        />
      ) : null}
    </Card>
  );
}
