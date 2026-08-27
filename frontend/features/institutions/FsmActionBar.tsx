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

/**
 * Shape of a mutation hook usable by the action bar. Child entities
 * (sede/facultad/center) pass their own transition hook via `transition`;
 * the root institution uses the default.
 */
export interface FsmTransitionLike {
  mutate: (
    variables: { id: string; action: string },
    options?: {
      onSuccess?: (data: unknown) => void;
      onError?: (error: unknown) => void;
    },
  ) => void;
  isPending: boolean;
}

interface FsmActionBarProps {
  entityId: string;
  state: string;
  /**
   * Transition mutation. Defaults to the institution transition; child
   * pages pass useSedeTransition/useFacultadTransition/useCenterTransition.
   */
  transition?: FsmTransitionLike;
  /** Entity label for success toasts (Spanish). Default "Institución". */
  entityLabel?: string;
  /** Write-role threshold for FSM actions. Defaults to superadmin. */
  minRoles?: string[];
}

export function FsmActionBar({
  entityId,
  state,
  transition,
  entityLabel = "Institución",
  minRoles = ["superadmin"],
}: FsmActionBarProps) {
  const roles = useAuthStore((s) => s.roles);
  const defaultTransition = useInstitutionTransition();
  const activeTransition = transition ?? defaultTransition;
  const [confirmAction, setConfirmAction] = useState<FsmAction | null>(null);

  const actions = getEntityActions(state, roles, minRoles);

  function runAction(action: FsmAction) {
    activeTransition.mutate(
      { id: entityId, action: action.name },
      {
        onSuccess: () => {
          toast.success(`${entityLabel} ${action.label.toLowerCase()}.`);
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
          disabled={activeTransition.isPending}
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
