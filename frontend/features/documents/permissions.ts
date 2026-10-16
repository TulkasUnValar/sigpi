/**
 * Documents feature authorization helpers.
 *
 * Permission model (derived from the backend role hierarchy):
 *   - Upload/edit: any role with level ≤ 6. This covers Superadmin(1),
 *     Admin(2), Director(3), Researcher(4), Evaluador(5), Asistente(6).
 *     Auditor(7) is read-only by design.
 *   - View: all authenticated users can view documents (the backend
 *     enforces session auth on every endpoint).
 *
 * Design (server-state): delegates to the shared `roleLevel` helper
 * from the reports feature so the role hierarchy stays DRY.
 */

import { roleLevel } from "@/features/reports/permissions";

/**
 * Whether the user may upload or edit documents.
 * Roles with level ≤ 6 can upload; Auditor (7) cannot.
 */
export function canUploadDocuments(roles: string[]): boolean {
  return roles.some((r) => roleLevel(r) <= 6);
}

/**
 * Whether the user may view documents.
 * All authenticated users can view; the backend enforces session auth.
 */
export function canViewDocuments(): boolean {
  return true;
}
