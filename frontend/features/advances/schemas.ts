/**
 * Advance schemas — zod validation for the create and edit forms.
 *
 * Fields per spec (advances-ui create): period, %, activities,
 * difficulties, next steps.
 *
 * Backend constraints mirrored here:
 *   - RN-P01: 0 <= cumulative_percentage <= 100.
 *   - RN-P02: period_end >= period_start.
 *
 * RF-043: create and edit share the same writable-field rules. The
 * `project` is chosen by the create route/select and is NOT editable:
 * the edit schema omits it and the backend strips it on PATCH.
 */

import { z } from "zod";

/** Percentage is coerced from the form's string input into a number. */
const percentageSchema = z.preprocess(
  (value) => (value === "" || value === undefined ? undefined : value),
  z.coerce
    .number({ invalid_type_error: "El porcentaje debe ser un número." })
    .min(0, "El porcentaje debe estar entre 0 y 100.")
    .max(100, "El porcentaje debe estar entre 0 y 100."),
);

/** Shared writable-field object (before the date refine) — RF-043. */
const advanceFieldsObject = z.object({
  period_start: z.string().min(1, "La fecha de inicio del período es obligatoria."),
  period_end: z.string().min(1, "La fecha de fin del período es obligatoria."),
  cumulative_percentage: percentageSchema,
  description: z.string().min(1, "La descripción es obligatoria."),
  activities: z.string().min(1, "Las actividades son obligatorias."),
  difficulties: z.string().optional().default(""),
  next_steps: z.string().optional().default(""),
});

/** RN-P02: period_end must be on or after period_start. */
function hasValidPeriod(data: { period_start: string; period_end: string }): boolean {
  return !data.period_start || !data.period_end || data.period_end >= data.period_start;
}

/** Create-form schema — validates the string-typed form draft. */
export const advanceCreateSchema = advanceFieldsObject.refine(hasValidPeriod, {
  message: "La fecha de fin debe ser posterior o igual a la de inicio.",
  path: ["period_end"],
});

/**
 * Edit-form schema — same rules as create; `project` is stripped from the
 * parsed output because it is not editable on PATCH (RF-043).
 */
export const advanceEditSchema = advanceCreateSchema;

/**
 * Create-form schema including the project select. Edit mode uses
 * `advanceEditSchema` instead — the project field is not rendered.
 */
export const advanceFormSchema = advanceFieldsObject
  .extend({
    project: z.string().min(1, "El proyecto es obligatorio."),
  })
  .refine(hasValidPeriod, {
    message: "La fecha de fin debe ser posterior o igual a la de inicio.",
    path: ["period_end"],
  });

/** Form draft shape — percentage arrives as a string from the input. */
export type AdvanceDraft = {
  period_start: string;
  period_end: string;
  cumulative_percentage: string;
  description: string;
  activities: string;
  difficulties: string;
  next_steps: string;
};

/** AdvanceForm values — the create draft plus the project select (RF-043). */
export type AdvanceFormValues = AdvanceDraft & { project: string };
