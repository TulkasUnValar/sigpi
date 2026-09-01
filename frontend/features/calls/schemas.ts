/**
 * Calls form schema — zod validation mirroring the DRF serializer.
 *
 * Rules (CallSerializer.validate):
 *   - external_entity required for external calls, forbidden for internal.
 *   - end dates on or after start dates (submission + evaluation).
 *
 * buildCallPayload projects the form values onto the writable fields:
 * read-only institution/status/timestamps are never sent and
 * external_entity is omitted for internal calls.
 */

import { z } from "zod";

import type { CallType, CreateCallPayload } from "@/features/calls/types";

/** Writable call form values (dates are native date-input strings). */
export const callFormSchema = z
  .object({
    title: z.string().min(1, "El título es obligatorio."),
    description: z.string().min(1, "La descripción es obligatoria."),
    call_type: z.enum(["internal", "external"], {
      errorMap: () => ({ message: "El tipo de convocatoria es obligatorio." }),
    }),
    external_entity: z.string().default(""),
    submission_start: z.string().optional(),
    submission_end: z.string().optional(),
    evaluation_start: z.string().optional(),
    evaluation_end: z.string().optional(),
  })
  .superRefine((data, ctx) => {
    if (data.call_type === "external" && !data.external_entity.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["external_entity"],
        message:
          "La entidad externa es obligatoria para convocatorias externas.",
      });
    }
    if (data.call_type === "internal" && data.external_entity.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["external_entity"],
        message: "Las convocatorias internas no pueden tener una entidad externa.",
      });
    }
    if (
      data.submission_start &&
      data.submission_end &&
      data.submission_end < data.submission_start
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["submission_end"],
        message:
          "El cierre de postulación debe ser posterior o igual al inicio de postulación.",
      });
    }
    if (
      data.evaluation_start &&
      data.evaluation_end &&
      data.evaluation_end < data.evaluation_start
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["evaluation_end"],
        message:
          "El fin de evaluación debe ser posterior o igual al inicio de evaluación.",
      });
    }
  });

/** Form values inferred from the schema. */
export type CallFormValues = z.infer<typeof callFormSchema>;

/**
 * Project form values onto the writable API payload.
 * - external_entity only for external calls.
 * - Empty date strings are dropped; read-only fields never included.
 */
export function buildCallPayload(values: CallFormValues): CreateCallPayload {
  const payload: CreateCallPayload = {
    title: values.title,
    description: values.description,
    call_type: values.call_type as CallType,
  };

  if (values.call_type === "external") {
    payload.external_entity = values.external_entity;
  }
  if (values.submission_start) payload.submission_start = values.submission_start;
  if (values.submission_end) payload.submission_end = values.submission_end;
  if (values.evaluation_start) payload.evaluation_start = values.evaluation_start;
  if (values.evaluation_end) payload.evaluation_end = values.evaluation_end;

  return payload;
}