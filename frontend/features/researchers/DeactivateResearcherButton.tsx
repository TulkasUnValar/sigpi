"use client";

/**
 * DeactivateResearcherButton — admin+ deactivate action with ConfirmDialog.
 *
 * Spec (researchers-ui deactivate):
 *   - One `deactivate` action (admin+, level ≤ 2) POSTs
 *     /api/researchers/{id}/deactivate/ behind a destructive ConfirmDialog.
 *   - Non-admin roles see no action; inactive researchers have no action.
 *   - On success the whole researchers cache invalidates.
 */

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { getErrorMessage } from "@/lib/errors";
import { useAuthStore } from "@/store/auth";
import { useDeactivateResearcher } from "@/features/researchers/mutations";
import { canDeactivateResearcher } from "@/features/researchers/permissions";

interface DeactivateResearcherButtonProps {
  researcherId: string;
  /** Current lifecycle state — only active researchers can be deactivated. */
  state: string;
}

export function DeactivateResearcherButton({
  researcherId,
  state,
}: DeactivateResearcherButtonProps) {
  const roles = useAuthStore((s) => s.roles);
  const deactivate = useDeactivateResearcher();
  const [confirmOpen, setConfirmOpen] = useState(false);

  if (!canDeactivateResearcher(roles) || state !== "active") return null;

  function runDeactivate() {
    deactivate.mutate(researcherId, {
      onSuccess: () => {
        toast.success("Investigador desactivado.");
      },
      onError: (error) => {
        toast.error(getErrorMessage(error));
      },
    });
  }

  return (
    <>
      <Button
        variant="destructive"
        size="sm"
        disabled={deactivate.isPending}
        onClick={() => setConfirmOpen(true)}
      >
        Desactivar
      </Button>
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="¿Confirmar desactivación?"
        description="El investigador dejará de estar activo. Esta acción no se puede deshacer."
        confirmLabel="Desactivar"
        cancelLabel="Cancelar"
        destructive
        onConfirm={runDeactivate}
      />
    </>
  );
}
