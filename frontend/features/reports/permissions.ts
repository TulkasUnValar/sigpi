/**
 * Reports authorization helpers — RB-001 role gating.
 *
 * RB-001:
 *   - canGenerateReport: preview/PDF require role level ≤ 4; admin-level
 *     roles (level ≤ 2) bypass.
 *   - canApproveReport: requires center director (role level ≤ 3) plus
 *     membership of the entity's center; superadmin bypasses.
 *
 * Role levels mirror the backend `accounts` hierarchy (7 fixed roles).
 */

/** Role levels mirroring the backend accounts hierarchy. */
const ROLE_LEVELS: Record<string, number> = {
  superadmin: 1,
  admin: 2,
  director: 3,
  director_centro: 4,
  researcher: 5,
  coinvestigator: 5,
  committee: 6,
  auditor: 7,
};

/** Admin-level role names (level ≤ 2). */
const ADMIN_PLUS_ROLES = ["admin", "superadmin"];

/** Level assigned to roles not in the fixed hierarchy (never privileged). */
const UNKNOWN_ROLE_LEVEL = 99;

/** Level of a role name (99 for unknown roles — never privileged). */
export function roleLevel(role: string): number {
  return ROLE_LEVELS[role] ?? UNKNOWN_ROLE_LEVEL;
}

/** Whether the user holds an admin+ role (level ≤ 2). */
export function isAdminPlus(roles: string[]): boolean {
  return roles.some((r) => ADMIN_PLUS_ROLES.includes(r));
}

/** Whether the user holds a director-level role (level ≤ 3). */
export function isDirector(roles: string[]): boolean {
  return roles.some((r) => roleLevel(r) <= 3);
}

/**
 * Whether the user may generate/preview/download reports (RB-001):
 * role level ≤ 4, with an admin-level (≤ 2) bypass.
 */
export function canGenerateReport(roles: string[]): boolean {
  if (isAdminPlus(roles)) return true;
  return roles.some((r) => roleLevel(r) <= 4);
}

/**
 * Whether the user may approve a report (RB-001 / RN-016):
 * center director (level ≤ 3) + membership of the entity's center;
 * superadmin bypasses. When no entity center is known, the check is
 * level-only (callers pass the center when available).
 */
export function canApproveReport(
  roles: string[],
  centers: { id: string; name?: string }[] = [],
  entityCenterId: string | null = null,
): boolean {
  if (roles.includes("superadmin")) return true;
  if (!isDirector(roles)) return false;
  if (!entityCenterId) return true;
  return centers.some((c) => c.id === entityCenterId);
}
