"use client";

/**
 * FsmActionBar — renders the advance state transitions available for the
 * current user's role and the advance's current state.
 *
 * - Visible actions come from getAdvanceActions(state, roles).
 * - Destructive transitions (reject) open a ConfirmDialog before the
 *   mutation is issued.
 * - On success the advances + dashboard + projects caches are invalidated.
 * - On failure a normalized error is shown and the cache is untouched.
 */

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { getErrorMessage } from "@/lib/errors";
import { useAuthStore } from "@/store/auth";
import { useAdvanceTransition } from "@/features/advances/mutations";
import {
  getAdvanceActions,
  isDestructiveAdvanceAction,
  type AdvanceAction,
} from "@/features/advances/fsm";

interface FsmActionBarProps {
  advanceId: string;
  state: string;
}

export function FsmActionBar({ advanceId, state }: FsmActionBarProps) {
  const roles = useAuthStore((s) => s.roles);
  const transition = useAdvanceTransition();
  const [confirmAction, setConfirmAction] = useState<AdvanceAction | null>(null);

  const actions = getAdvanceActions(state, roles);

  function runAction(action: AdvanceAction) {
    transition.mutate(
      { id: advanceId, action: action.name },
      {
        onSuccess: () => {
          toast.success(`Avance ${action.label.toLowerCase()}.`);
        },
        onError: (error) => {
          toast.error(getErrorMessage(error));
        },
      },
    );
  }

  function handleClick(action: AdvanceAction) {
    if (isDestructiveAdvanceAction(action.name)) {
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
          variant={isDestructiveAdvanceAction(action.name) ? "destructive" : "default"}
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