"use client";

/**
 * FsmActionBar — renders the institution lifecycle transitions available
 * for the current user's role and the entity's current state.
 *
 * Spec (institutions-ui RF-F04):
 *   - Visible actions come from getEntityActions(state, roles).
 *   - Destructive transitions (deactivate, archive) open a ConfirmDialog
 *     before the mutation is issued.
 *   - Archived is terminal — no transition actions appear.
 *   - On success the whole institutions cache invalidates.
 *   - On failure a normalized error is shown and the cache is untouched.
 */

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { getErrorMessage } from "@/lib/errors";
import { useAuthStore } from "@/store/auth";
import { useInstitutionTransition } from "@/features/institutions/mutations";
import {
  getEntityActions,
  isDestructiveEntityAction,
  type FsmAction,
} from "@/features/institutions/fsm";

interface FsmActionBarProps {
  entityId: string;
  state: string;
}

export function FsmActionBar({ entityId, state }: FsmActionBarProps) {
  const roles = useAuthStore((s) => s.roles);
  const transition = useInstitutionTransition();
  const [confirmAction, setConfirmAction] = useState<FsmAction | null>(null);

  const actions = getEntityActions(state, roles);

  function runAction(action: FsmAction) {
    transition.mutate(
      { id: entityId, action: action.name },
      {
        onSuccess: () => {
          toast.success(`Institución ${action.label.toLowerCase()}.`);
        },
        onError: (error) => {
          toast.error(getErrorMessage(error));
        },
      },
    );
  }

  function handleClick(action: FsmAction) {
    if (isDestructiveEntityAction(action.name)) {
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
          key={`${action.name}-${action.fromStates.join("|")}`}
          variant={isDestructiveEntityAction(action.name) ? "destructive" : "default"}
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
