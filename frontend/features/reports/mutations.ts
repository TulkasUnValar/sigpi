"use client";

/**
 * Reports mutations — approval.
 *
 * Spec (frontend-reports / RB-002):
 *   - useApproveReport POSTs .../approve/ with the active institution scope.
 *   - On success it invalidates the entity roots (projects, researchers,
 *     institutions) and the derived reports view so lists refetch.
 *   - A 409 (RN-017) surfaces the server message verbatim and does NOT
 *     invalidate anything (the backend remains authoritative).
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { buildApproveUrl } from "@/features/reports/constants";
import type { ReportApprovalResponse, ReportType } from "@/features/reports/types";

function useInstitutionId(): string | null {
  return useAuthStore((s) => s.activeInstitution?.id ?? null);
}

/** Approve a report — POST /api/reports/{type}/{id}/approve/ (RN-016). */
export function useApproveReport() {
  const qc = useQueryClient();
  const institutionId = useInstitutionId();
  return useMutation({
    mutationFn: ({ type, entityId }: { type: ReportType; entityId: string }) =>
      api.post<ReportApprovalResponse>(buildApproveUrl(type, entityId), undefined, {
        institutionId,
      }),
    onSuccess: () => {
      // Entity roots + derived reports view; 409/4xx/5xx never reach here
      // (RB-002 — a failed approval invalidates nothing).
      void qc.invalidateQueries({ queryKey: ["projects"] });
      void qc.invalidateQueries({ queryKey: ["researchers"] });
      void qc.invalidateQueries({ queryKey: ["institutions"] });
      void qc.invalidateQueries({ queryKey: ["reports"] });
    },
  });
}
