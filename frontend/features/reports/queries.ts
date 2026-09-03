"use client";

/**
 * Reports TanStack Query hooks — preview + derived entity options.
 *
 * Spec (frontend-reports):
 *   - useReportPreview calls GET /api/reports/{type}/{id}/preview/ with the
 *     active institution scope and stays disabled without a target.
 *   - useReportEntityOptions derives per-type entity options from the
 *     EXISTING entity hooks (useProjectsList / useResearchersList /
 *     useCenters); advances maps to projects (RB-004 — no invented
 *     reports-list endpoint).
 */

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { useAuthStore } from "@/store/auth";
import { buildPreviewUrl } from "@/features/reports/constants";
import { resolveSelectorKind } from "@/features/reports/schemas";
import { useProjectsList, useCenters } from "@/features/projects/queries";
import { useResearchersList } from "@/features/researchers/queries";
import type { ReportPreview, ReportType } from "@/features/reports/types";

/** Active institution id from the auth store (drives X-Institution-ID). */
export function useActiveInstitutionId(): string | null {
  return useAuthStore((s) => s.activeInstitution?.id ?? null);
}

/** Fetch the HTML preview for a report target — GET .../preview/. */
export function useReportPreview(type: ReportType | null, entityId: string | null) {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: queryKeys.reports.preview(institutionId, type, entityId),
    queryFn: () =>
      api.get<ReportPreview>(buildPreviewUrl(type as ReportType, entityId as string), {
        institutionId,
      }),
    enabled: Boolean(type && entityId),
  });
}

/** A selectable report entity (id + display name). */
export interface ReportEntityOption {
  id: string;
  name: string;
}

/**
 * Entity options for a report type, derived from the existing list hooks.
 * `advances` deliberately resolves to the project selector (RB-004).
 */
export function useReportEntityOptions(type: ReportType) {
  const kind = resolveSelectorKind(type);
  const projects = useProjectsList();
  const researchers = useResearchersList();
  const centers = useCenters();

  const options: ReportEntityOption[] =
    kind === "project"
      ? (projects.data?.results ?? []).map((p) => ({ id: p.id, name: p.title }))
      : kind === "researcher"
        ? (researchers.data?.results ?? []).map((r) => ({ id: r.id, name: r.full_name }))
        : (centers.data ?? []).map((c) => ({ id: c.id, name: c.name }));

  const isLoading =
    kind === "project"
      ? projects.isLoading
      : kind === "researcher"
        ? researchers.isLoading
        : centers.isLoading;

  return { options, isLoading };
}
