"use client";

/**
 * Projects mutations — create and FSM transitions.
 *
 * Spec (server-state):
 *   - Every FSM mutation invalidates its resource and all derived queries
 *     (dashboard KPIs, detail, lists).
 *   - On mutation failure the cache is NOT invalidated and the error is shown.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useActiveInstitutionId } from "@/features/projects/queries";
import type { CreateProjectPayload, ProjectDetail } from "@/features/projects/types";

/** Invalidate every query derived from the projects resource. */
function invalidateProjects(qc: ReturnType<typeof useQueryClient>) {
  void qc.invalidateQueries({ queryKey: ["projects"] });
  void qc.invalidateQueries({ queryKey: ["dashboard"] });
}

/** Create a project and invalidate the projects/dashboard caches. */
export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateProjectPayload) =>
      api.post<ProjectDetail>("/api/projects/", payload),
    onSuccess: () => invalidateProjects(qc),
  });
}

/**
 * Trigger a project FSM transition. `action` is the DRF endpoint action
 * (e.g. "approve", "reject"). The current state is returned by the API;
 * on success all derived caches are invalidated.
 */
export function useProjectTransition() {
  const qc = useQueryClient();
  const institutionId = useActiveInstitutionId();
  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: string }) =>
      api.post<ProjectDetail>(`/api/projects/${id}/${action}/`, {}, {
        institutionId,
      }),
    onSuccess: () => invalidateProjects(qc),
  });
}
