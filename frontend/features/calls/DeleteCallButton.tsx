"use client";

/**
 * DeleteCallButton — gated destructive delete for a call.
 *
 * Spec (calls-ui gated delete):
 *   - Only visible for `borrador` calls with ZERO linked CallProjects.
 *   - Confirms via a destructive ConfirmDialog before DELETE.
 *   - On success: success toast + redirect to /calls.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { getErrorMessage } from "@/lib/errors";
import { useAuthStore } from "@/store/auth";
import { canManageCall } from "@/features/calls/permissions";
import { useCallProjects } from "@/features/calls/queries";
import { useDeleteCall } from "@/features/calls/mutations";
import type { Call } from "@/features/calls/types";

interface DeleteCallButtonProps {
  call: Call;
}

export function DeleteCallButton({ call }: DeleteCallButtonProps) {
  const router = useRouter();
  const roles = useAuthStore((s) => s.roles);
  const projectsQuery = useCallProjects(call.id);
  const deleteCall = useDeleteCall();

  const [confirmOpen, setConfirmOpen] = useState(false);

  const linkedCount = projectsQuery.data?.count ?? 0;
  const canDelete = canManageCall(roles) && call.status === "borrador" && linkedCount === 0;

  if (!canDelete) return null;

  function handleConfirm() {
    deleteCall.mutate(call.id, {
      onSuccess: () => {
        toast.success("Convocatoria eliminada.");
        router.push("/calls");
      },
      onError: (error) => toast.error(getErrorMessage(error)),
    });
  }

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        className="text-destructive hover:text-destructive"
        onClick={() => setConfirmOpen(true)}
        disabled={deleteCall.isPending}
      >
        <Trash2 className="mr-1 h-4 w-4" />
        Eliminar
      </Button>
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="¿Eliminar convocatoria?"
        description="Esta acción elimina la convocatoria de forma permanente y no se puede deshacer."
        confirmLabel="Eliminar"
        cancelLabel="Cancelar"
        destructive
        onConfirm={handleConfirm}
      />
    </>
  );
}
