"use client";

/**
 * FsmActionBar — renders the project state transitions available for the
 * current user's role and the project's current state.
 *
 * - Visible actions come from getProjectActions(state, roles).
 * - Destructive transitions (reject/cancel/close) open a ConfirmDialog
 *   before the mutation is issued.
 * - On success the projects + dashboard caches are invalidated.
 * - On failure a normalized error is shown and the cache is untouched.
 */

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { getErrorMessage } from "@/lib/errors";
import { useAuthStore } from "@/store/auth";
import { useProjectTransition } from "@/features/projects/mutations";
import {
  getProjectActions,
  isDestructiveAction,
  type ProjectAction,
} from "@/features/projects/fsm";

interface FsmActionBarProps {
  projectId: string;
  state: string;
}

export function FsmActionBar({ projectId, state }: FsmActionBarProps) {
  const roles = useAuthStore((s) => s.roles);
  const transition = useProjectTransition();
  const [confirmAction, setConfirmAction] = useState<ProjectAction | null>(null);

  const actions = getProjectActions(state, roles);

  function runAction(action: ProjectAction) {
    transition.mutate(
      { id: projectId, action: action.name },
      {
        onSuccess: () => {
          toast.success(`Proyecto ${action.label.toLowerCase()}.`);
        },
        onError: (error) => {
          toast.error(getErrorMessage(error));
        },
      },
    );
  }

  function handleClick(action: ProjectAction) {
    if (isDestructiveAction(action.name)) {
      setConfirmAction(action);
      return;
    }
    runAction(action);
  }

  if (actions.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2" aria-label="Acciones de estado">
      {actions.map((action) => (
        <Button
          key={action.name}
          variant={isDestructiveAction(action.name) ? "destructive" : "default"}
          size="sm"
          disabled={transition.isPending}
          onClick={() => handleClick(action)}
        >
          {action.label}
        </Button>
      ))}

      {confirmAction ? (
        <ConfirmDialog
          open={Boolean(confirmAction)}
          onOpenChange={(open) => {
            if (!open) setConfirmAction(null);
          }}
          title={`¿Confirmar "${confirmAction.label}"?`}
          description="Esta acción no se puede deshacer."
          confirmLabel={confirmAction.label}
          cancelLabel="Cancelar"
          destructive
          onConfirm={() => runAction(confirmAction)}
        />
      ) : null}
    </div>
  );
}
