/**
 * Institutions FSM action configuration.
 *
 * Maps the backend lifecycle state machine to frontend actions, filtered
 * by (state, role). Mirrors the backend permission matrix (views.py):
 *
 *   active      → deactivate, archive
 *   deactivated → activate, archive
 *   archived    → terminal (no outbound transitions)
 *
 * Institution-level writes are superadmin-only (IsSuperAdmin). The
 * destructive transitions (deactivate, archive) require a ConfirmDialog
 * per the spec (RF-F04).
 */

import type { FsmAction } from "@/features/institutions/types";

export type { FsmAction } from "@/features/institutions/types";

const SUPERADMIN = "superadmin";

/** Complete transition table (3 backend actions). */
export const ENTITY_ACTIONS: FsmAction[] = [
  {
    name: "activate",
    label: "Activar",
    destructive: false,
    allowedRoles: [SUPERADMIN],
    fromStates: ["deactivated"],
  },
  {
    name: "deactivate",
    label: "Desactivar",
    destructive: true,
    allowedRoles: [SUPERADMIN],
    fromStates: ["active"],
  },
  {
    name: "archive",
    label: "Archivar",
    destructive: true,
    allowedRoles: [SUPERADMIN],
    fromStates: ["active", "deactivated"],
  },
];

/** Terminal state — no outbound transitions. */
const TERMINAL_STATES = new Set(["archived"]);

/**
 * Return the actions visible for an entity in `state` for a user with
 * `roles`. Filters by source state and allowed role.
 *
 * `minRoles` optionally overrides the write-role threshold: child entities
 * (sede/facultad/center) use ["admin", "superadmin"] (RF-F05) while the
 * root institution stays superadmin-only. When omitted the per-action
 * `allowedRoles` from the config table applies.
 */
export function getEntityActions(state: string, roles: string[], minRoles?: string[]): FsmAction[] {
  if (TERMINAL_STATES.has(state)) return [];

  const roleSet = new Set(roles);
  return ENTITY_ACTIONS.filter((a) => {
    if (!a.fromStates.includes(state)) return false;
    if (minRoles) return minRoles.some((r) => roleSet.has(r));
    return a.allowedRoles.some((r) => roleSet.has(r));
  });
}

/** Whether an action requires a destructive confirmation. */
export function isDestructiveEntityAction(name: string): boolean {
  return name === "deactivate" || name === "archive";
}
