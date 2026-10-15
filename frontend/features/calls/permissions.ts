/**
 * Calls feature permissions — UI-side authorization helpers.
 *
 * Mirrors the backend CanManageCall permission (level <= 3):
 * director, admin and superadmin may create, edit, delete and drive calls.
 * The auth store emits role slugs (e.g., "director", "admin", "superadmin").
 *
 * The backend remains authoritative; these helpers only shape affordances.
 */

/** Roles allowed to manage calls (create/edit/delete/FSM). */
export const MANAGER_ROLES = ["director", "admin", "superadmin"] as const;

/** Whether any of the given roles may manage calls. */
export function canManageCall(roles: string[]): boolean {
  return roles.some((role) => (MANAGER_ROLES as readonly string[]).includes(role));
}
