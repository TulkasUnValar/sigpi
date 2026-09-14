"use client";

/**
 * FsmActionBar — renders the advance state transitions available for the
 * current user's role and the advance's current state.
 *
 * - Visible actions come from getAdvanceActions(state, roles).
 * - observe/reject collect `review_text` through a dialog with a textarea
 *   before the mutation is issued; confirmation is disabled for blank
 *   text (RF-041).
 * - On success the advances + dashboard + projects caches are invalidated.
 * - On failure a normalized error is shown and the cache is untouched.
 */

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { getErrorMessage } from "@/lib/errors";
import { useAuthStore } from "@/store/auth";
import { useAdvanceTransition } from "@/features/advances/mutations";
import {
  getAdvanceActions,
  isDestructiveAdvanceAction,
  needsReviewText,
  type AdvanceAction,
} from "@/features/advances/fsm";

interface FsmActionBarProps {
  advanceId: string;
  state: string;
}

const TEXTAREA_CLASSES =
  "min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

export function FsmActionBar({ advanceId, state }: FsmActionBarProps) {
  const roles = useAuthStore((s) => s.roles);
  const transition = useAdvanceTransition();
  const [reviewAction, setReviewAction] = useState<AdvanceAction | null>(null);
  const [reviewText, setReviewText] = useState("");

  const actions = getAdvanceActions(state, roles);

  function runAction(action: AdvanceAction, reviewText?: string) {
    transition.mutate(
      { id: advanceId, action: action.name, review_text: reviewText },
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

  function closeReviewDialog() {
    setReviewAction(null);
    setReviewText("");
  }

  function handleClick(action: AdvanceAction) {
    if (needsReviewText(action.name)) {
      setReviewText("");
      setReviewAction(action);
      return;
    }
    runAction(action);
  }

  function handleConfirmReview() {
    if (!reviewAction) return;
    runAction(reviewAction, reviewText.trim());
    closeReviewDialog();
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

      {reviewAction ? (
        <Dialog
          open
          onOpenChange={(open) => {
            if (!open) closeReviewDialog();
          }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>¿Confirmar &quot;{reviewAction.label}&quot;?</DialogTitle>
              <DialogDescription>
                Escribe el comentario de revisión antes de continuar. Esta acción no se puede
                deshacer.
              </DialogDescription>
            </DialogHeader>
            <div>
              <Label htmlFor="review-text">Comentario de revisión</Label>
              <textarea
                id="review-text"
                className={TEXTAREA_CLASSES}
                value={reviewText}
                onChange={(e) => setReviewText(e.target.value)}
                placeholder="Detalla el motivo de la revisión…"
              />
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={closeReviewDialog}>
                Cancelar
              </Button>
              <Button
                variant={isDestructiveAdvanceAction(reviewAction.name) ? "destructive" : "default"}
                disabled={!reviewText.trim() || transition.isPending}
                onClick={handleConfirmReview}
              >
                {reviewAction.label}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      ) : null}
    </div>
  );
}
