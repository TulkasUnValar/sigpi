/**
 * Researchers FSM action configuration.
 *
 * Spec (researchers-ui deactivate): the backend exposes a single lifecycle
 * transition — `deactivate` (POST /api/researchers/{id}/deactivate/),
 * admin+ (level ≤ 2). There is NO activate/archive/me endpoint, so the
 * frontend models only this one transition. Reactivation is handled by
 * the edit PATCH with `is_active: true`.
 */

import type { FsmAction } from "@/features/institutions/types";

export type { FsmAction };

/** Roles allowed to deactivate a researcher (admin+ = level ≤ 2). */
const DEACTIVATE_ROLES = ["admin", "superadmin"];

/** Complete lifecycle transition table (single deactivate action). */
export const RESEARCHER_ACTIONS: FsmAction[] = [
  {
    name: "deactivate",
    label: "Desactivar",
    destructive: true,
    allowedRoles: DEACTIVATE_ROLES,
    fromStates: ["active"],
  },
];

/**
 * Return the researcher lifecycle actions visible for `state` and `roles`.
 * Only `deactivate` exists; it requires admin+ and an active researcher.
 */
export function getResearcherActions(state: string, roles: string[]): FsmAction[] {
  const roleSet = new Set(roles);
  return RESEARCHER_ACTIONS.filter((a) => {
    if (!a.fromStates.includes(state)) return false;
    return a.allowedRoles.some((r) => roleSet.has(r));
  });
}

/** Whether an action is the researcher deactivate (destructive) transition. */
export function isResearcherDeactivate(name: string): boolean {
  return name === "deactivate";
}
