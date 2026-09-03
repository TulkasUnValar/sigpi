"use client";

/**
 * PreviewDialog — sandboxed iframe HTML preview (RF-003).
 *
 * The preview HTML from GET /api/reports/{type}/{id}/preview/ is rendered
 * via <iframe sandbox srcDoc> WITHOUT allow-same-origin: WeasyPrint output
 * is untrusted markup, so it must not touch the host origin (no scripts,
 * no same-origin storage). Loading and 403/404/500 error states render
 * instead of the iframe — no HTML is shown on failure.
 */

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { getErrorMessage } from "@/lib/errors";
import { getReportTypeLabel } from "@/features/reports/constants";
import { useReportPreview } from "@/features/reports/queries";
import type { ReportTarget } from "@/features/reports/types";
import { useEffect } from "react";

interface PreviewDialogProps {
  /** Selected report target; null closes the dialog and disables the query. */
  target: ReportTarget | null;
  /** Called when the dialog is dismissed. */
  onClose: () => void;
  /** Called when preview data loads successfully. */
  onSuccess?: () => void;
}

export function PreviewDialog({ target, onClose, onSuccess }: PreviewDialogProps) {
  const { data, isLoading, isError, error } = useReportPreview(
    target?.type ?? null,
    target?.entityId ?? null,
  );

  // Notify parent on successful preview load.
  useEffect(() => {
    if (data && onSuccess) {
      onSuccess();
    }
  }, [data, onSuccess]);

  const title = target
    ? `Vista previa — ${getReportTypeLabel(target.type)}`
    : "Vista previa";

  return (
    <Dialog
      open={target !== null}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            {target ? `Entidad: ${target.entityName}` : "Previsualización del informe"}
          </DialogDescription>
        </DialogHeader>

        {isLoading && (
          <p role="status" className="text-sm text-muted-foreground">
            Generando vista previa…
          </p>
        )}

        {isError && (
          <div
            role="alert"
            className="rounded-md border border-destructive/50 p-4 text-sm text-destructive"
          >
            {getErrorMessage(error)}
          </div>
        )}

        {data && !isError && (
          <iframe
            sandbox=""
            srcDoc={data.html}
            title="Vista previa del informe"
            className="h-[60vh] w-full rounded-md border"
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
