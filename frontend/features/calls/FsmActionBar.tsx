"use client";

/**
 * FsmActionBar — renders the call state transitions available for the
 * current user's role and the call's current state.
 *
 * - Visible actions come from getCallActions(state, roles).
 * - Only `archive` is destructive and opens a ConfirmDialog first.
 * - On success the calls caches are invalidated; on failure the error
 *   is surfaced via the Toaster and the cache is untouched.
 */

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { getErrorMessage } from "@/lib/errors";
import { useAuthStore } from "@/store/auth";
import { useCallTransition } from "@/features/calls/mutations";
import {
  getCallActions,
  isDestructiveCallAction,
  type CallAction,
} from "@/features/calls/fsm";

interface FsmActionBarProps {
  callId: string;
  state: string;
}

export function FsmActionBar({ callId, state }: FsmActionBarProps) {
  const roles = useAuthStore((s) => s.roles);
  const transition = useCallTransition();
  const [confirmAction, setConfirmAction] = useState<CallAction | null>(null);

  const actions = getCallActions(state, roles);

  function runAction(action: CallAction) {
    transition.mutate(
      { id: callId, action: action.name },
      {
        onSuccess: () => {
          toast.success(`${action.label}.`);
        },
        onError: (error) => {
          toast.error(getErrorMessage(error));
        },
      },
    );
  }

  function handleClick(action: CallAction) {
    if (isDestructiveCallAction(action.name)) {
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
          variant={isDestructiveCallAction(action.name) ? "destructive" : "default"}
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