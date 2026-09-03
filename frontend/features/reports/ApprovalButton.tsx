"use client";

/**
 * ApprovalButton — director-gated report approval (RF-005).
 *
 * Rendered only when canApproveReport passes (RB-001). Clicking "Aprobar"
 * triggers the POST /api/reports/{type}/{id}/approve/ mutation; success
 * updates the parent via onSuccess and shows a toast; 409 RN-017 surfaces
 * verbatim as a toast and does NOT invalidate queries (RB-002).
 */

import { useState } from "react";
import { CheckCircle } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { getErrorMessage } from "@/lib/errors";
import { useApproveReport } from "@/features/reports/mutations";
import { canApproveReport } from "@/features/reports/permissions";
import { useAuthStore } from "@/store/auth";
import type { ReportType } from "@/features/reports/types";

interface ApprovalButtonProps {
  /** Report type of the target entity. */
  type: ReportType;
  /** Entity id — the approval endpoint path segment. */
  entityId: string;
  /** Called when the approval succeeds. */
  onSuccess?: () => void;
}

export function ApprovalButton({ type, entityId, onSuccess }: ApprovalButtonProps) {
  const roles = useAuthStore((s) => s.roles);
  const [localPending, setLocalPending] = useState(false);
  const { mutateAsync, isPending } = useApproveReport();

  if (!canApproveReport(roles)) {
    return null;
  }

  const handleApprove = async () => {
    setLocalPending(true);
    try {
      await mutateAsync({ type, entityId });
      toast.success("Informe aprobado.");
      onSuccess?.();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setLocalPending(false);
    }
  };

  const pending = isPending || localPending;

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => void handleApprove()}
      disabled={pending}
    >
      <CheckCircle className="h-4 w-4" />
      {pending ? "Aprobando…" : "Aprobar"}
    </Button>
  );
}
