/**
 * Calls feature permissions — UI-side authorization helpers.
 *
 * Mirrors the backend CanManageCall permission (level <= 3):
 * director, director_centro, admin and superadmin may create, edit,
 * delete and drive calls. The auth store emits the raw backend role
 * name, so `director_centro` is included explicitly as an alias.
 *
 * The backend remains authoritative; these helpers only shape affordances.
 */

/** Roles allowed to manage calls (create/edit/delete/FSM). */
export const MANAGER_ROLES = ["director", "director_centro", "admin", "superadmin"] as const;

/** Whether any of the given roles may manage calls. */
export function canManageCall(roles: string[]): boolean {
  return roles.some((role) => (MANAGER_ROLES as readonly string[]).includes(role));
}
