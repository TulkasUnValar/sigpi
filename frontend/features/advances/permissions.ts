/**
 * Advance permission helpers.
 *
 * RF-043/044: edit/delete are gated to borrador; delete additionally
 * requires the authenticated creator. The backend 403 remains the
 * authorization backstop.
 */

import type { AdvanceDetail } from "@/features/advances/types";

/** Whether the advance can be edited (borrador only). */
export function canEditAdvance(advance: AdvanceDetail): boolean {
  return advance.status === "borrador";
}

/** Whether the advance can be deleted (borrador + creator only). */
export function canDeleteAdvance(advance: AdvanceDetail, userId: string | null): boolean {
  return advance.status === "borrador" && userId === advance.created_by;
}
