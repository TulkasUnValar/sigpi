/**
 * Advance create schema — zod validation for the create form.
 *
 * Fields per spec (advances-ui create): period, %, activities,
 * difficulties, next steps.
 *
 * Backend constraints mirrored here:
 *   - RN-P01: 0 <= cumulative_percentage <= 100.
 *   - RN-P02: period_end >= period_start.
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

/** Create-form schema — validates the string-typed form draft. */
export const advanceCreateSchema = z
  .object({
    period_start: z.string().min(1, "La fecha de inicio del período es obligatoria."),
    period_end: z.string().min(1, "La fecha de fin del período es obligatoria."),
    cumulative_percentage: percentageSchema,
    description: z.string().min(1, "La descripción es obligatoria."),
    activities: z.string().min(1, "Las actividades son obligatorias."),
    difficulties: z.string().optional().default(""),
    next_steps: z.string().optional().default(""),
  })
  .refine(
    (data) =>
      !data.period_start ||
      !data.period_end ||
      data.period_end >= data.period_start,
    {
      message: "La fecha de fin debe ser posterior o igual a la de inicio.",
      path: ["period_end"],
    },
  );

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