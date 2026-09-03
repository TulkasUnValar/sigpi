"use client";

/**
 * Reports page — protected /reports entry point.
 *
 * Spec (frontend-reports RF-001): the page role-gates the hub — users
 * without CanGenerateReport see a 403 message and the hub (with its
 * entity-list queries) never mounts, so no API calls are made.
 */

import { AuthenticatedLayout } from "@/components/shell/AuthenticatedLayout";
import { ReportHub } from "@/features/reports/ReportHub";
import { canGenerateReport } from "@/features/reports/permissions";
import { useAuthStore } from "@/store/auth";

export default function ReportsPage() {
  const roles = useAuthStore((s) => s.roles);

  if (!canGenerateReport(roles)) {
    return (
      <AuthenticatedLayout>
        <div
          role="alert"
          className="rounded-md border border-destructive p-4 text-sm"
        >
          No tiene permisos para generar informes.
        </div>
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <ReportHub />
    </AuthenticatedLayout>
  );
}
