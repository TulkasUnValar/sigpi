"use client";

/**
 * DownloadButton — authenticated blob PDF download (RF-004).
 *
 * Clicking "Descargar PDF" triggers the shared downloadBlob (fetch with
 * session credentials + X-Institution-ID → blob → objectURL → anchor click,
 * RF-004 — a plain href cannot send credentials and returns 401). While the
 * WeasyPrint generation request is in flight the button shows a pending
 * state and is disabled (<5s NFR); failures surface a Sonner toast with the
 * server message (403/404/500).
 */

import { useState } from "react";
import { Download } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { getErrorMessage } from "@/lib/errors";
import { buildPdfFilename, buildPdfUrl } from "@/features/reports/constants";
import { downloadBlob } from "@/features/reports/download";
import { useActiveInstitutionId } from "@/features/reports/queries";
import type { ReportType } from "@/features/reports/types";

interface DownloadButtonProps {
  /** Report type of the target entity. */
  type: ReportType;
  /** Entity id — the PDF endpoint path segment. */
  entityId: string;
}

export function DownloadButton({ type, entityId }: DownloadButtonProps) {
  const institutionId = useActiveInstitutionId();
  const [pending, setPending] = useState(false);

  const handleDownload = async () => {
    setPending(true);
    try {
      await downloadBlob(buildPdfUrl(type, entityId), buildPdfFilename(type), institutionId);
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setPending(false);
    }
  };

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => void handleDownload()}
      disabled={pending}
    >
      <Download className="h-4 w-4" />
      {pending ? "Generando PDF…" : "Descargar PDF"}
    </Button>
  );
}
