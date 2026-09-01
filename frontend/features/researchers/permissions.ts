/**
 * Researchers authorization helpers.
 *
 * Spec (researchers-ui):
 *   - update (edit/PATCH): self (owning researcher, level ≤ 4) or admin+
 *     (level ≤ 2). "Self" means the researcher profile is linked to the
 *     current user (detail.user === user.id).
 *   - deactivate: admin+ only (level ≤ 2).
 */

import type { Researcher } from "@/features/researchers/types";

/** Roles at admin+ level (level ≤ 2). */
const ADMIN_ROLES = ["admin", "superadmin"];

/** Whether the user holds an admin+ role (level ≤ 2). */
export function isAdminPlus(roles: string[]): boolean {
  return roles.some((r) => ADMIN_ROLES.includes(r));
}

/** Whether the user may deactivate a researcher (admin+, level ≤ 2). */
export function canDeactivateResearcher(roles: string[]): boolean {
  return isAdminPlus(roles);
}

/**
 * Whether the user may edit (PATCH) a researcher: admin+ always, or the
 * linked self (detail.user === current user id).
 */
export function canEditResearcher(
  detail: Pick<Researcher, "user">,
  currentUserId: string | null,
  roles: string[],
): boolean {
  if (isAdminPlus(roles)) return true;
  return Boolean(detail.user && currentUserId && detail.user === currentUserId);
}
