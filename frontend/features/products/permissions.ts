/**
 * Products feature permissions — flat all-authenticated policy.
 *
 * The backend products ViewSets use IsAuthenticated only, so every
 * authenticated role may render CRUD affordances. No RoleGuard exists;
 * these helpers exist so callers express the policy explicitly.
 */

/** Whether the given roles may manage products (always true — flat). */
export function canManageProducts(_roles: string[]): boolean {
  return true;
}
