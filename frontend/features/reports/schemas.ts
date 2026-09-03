/**
 * Reports schemas — zod validation of the generator selection.
 *
 * The generator picks a report type and an entity id; `advances` reports
 * target a project entity, so resolveSelectorKind maps advances → project
 * (the entity selector is fed by the projects hook, RB-004).
 */

import { z } from "zod";

import type { ReportSelectorKind, ReportType } from "@/features/reports/types";

/** The four report type codes accepted by the generator. */
export const REPORT_TYPE_VALUES: [ReportType, ...ReportType[]] = [
  "project",
  "researcher",
  "center",
  "advances",
];

/** Generator selection — validated `{type, entityId}`. */
export const reportSelectionSchema = z.object({
  type: z.enum(REPORT_TYPE_VALUES, {
    errorMap: () => ({ message: "El tipo de informe es obligatorio." }),
  }),
  entityId: z.string().min(1, "Debe seleccionar una entidad."),
});

/** Validated generator selection values. */
export type ReportSelection = z.infer<typeof reportSelectionSchema>;

/**
 * Map a report type to the entity-hook kind feeding the selector.
 * `advances` reports target a project entity.
 */
export function resolveSelectorKind(type: ReportType): ReportSelectorKind {
  return type === "advances" ? "project" : type;
}

/** Safe-parse a raw selection into validated values (null when invalid). */
export function parseReportSelection(input: unknown): ReportSelection | null {
  const result = reportSelectionSchema.safeParse(input);
  return result.success ? result.data : null;
}
