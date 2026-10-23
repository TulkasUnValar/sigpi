/**
 * Budgets permissions — role-based access control.
 *
 * Admin/director can create/update budgets and authorize over-executions.
 * Researcher has read-only access.
 * Follows the same pattern as calls/permissions.ts.
 */

import { useAuthStore } from "@/store/auth";

/** Roles that can manage budgets (create, update, delete). */
const MANAGE_ROLES = ["admin", "director"];

/** Roles that can authorize over-executions (RN-020). */
const AUTHORIZE_ROLES = ["admin", "director"];

/** Check if user can manage budgets (admin or director). */
export const canManageBudget = (roles: string[]): boolean => {
  return roles.some((role) => MANAGE_ROLES.includes(role));
};

/** Check if user can authorize over-executions (admin or director). */
export const canAuthorizeExecution = (roles: string[]): boolean => {
  return roles.some((role) => AUTHORIZE_ROLES.includes(role));
};

/** Hook to check budget permissions from auth store. */
export const useBudgetPermissions = () => {
  const roles = useAuthStore((state) => state.roles);

  return {
    canManage: canManageBudget(roles),
    canAuthorize: canAuthorizeExecution(roles),
    isReadOnly: !canManageBudget(roles),
  };
};
