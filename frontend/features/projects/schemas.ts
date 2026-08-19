/**
 * Project wizard step schemas — zod validation per step.
 *
 * basic → classification (center/group/line) → team → documents → review.
 * Each step has its own schema; the review step is a projection of the
 * collected data.
 */

import { z } from "zod";

/** Basic info step: title, abstract, objectives, methodology, dates. */
export const basicStepSchema = z
  .object({
    title: z.string().min(1, "El título es obligatorio."),
    abstract: z.string().min(1, "El resumen es obligatorio."),
    objectives: z.string().min(1, "Los objetivos son obligatorios."),
    methodology: z.string().min(1, "La metodología es obligatoria."),
    expected_results: z.string().min(1, "Los resultados esperados son obligatorios."),
    keywords: z.string().optional().default(""),
    start_date: z.string().min(1, "La fecha de inicio es obligatoria."),
    estimated_end_date: z.string().min(1, "La fecha de finalización es obligatoria."),
  })
  .refine(
    (data) => !data.start_date || !data.estimated_end_date ||
      data.estimated_end_date >= data.start_date,
    {
      message: "La fecha de finalización debe ser posterior a la de inicio.",
      path: ["estimated_end_date"],
    },
  );

/** Classification step: center required; group/line optional. */
export const classificationStepSchema = z.object({
  center: z.string().min(1, "El centro es obligatorio."),
  group: z.string().optional().default(""),
  line: z.string().optional().default(""),
});

/** Team step: members optional, but each must have a role. */
export const teamStepSchema = z.object({
  members: z
    .array(
      z.object({
        researcher: z.string().min(1),
        role: z.string().min(1, "El rol del integrante es obligatorio."),
      }),
    )
    .default([]),
});

/** Document step: documents optional. */
export const documentsStepSchema = z.object({
  documents: z
    .array(
      z.object({
        name: z.string().min(1, "El nombre del documento es obligatorio."),
        doc_type: z.string().min(1),
        external_url: z.string().min(1, "La URL del documento es obligatoria."),
      }),
    )
    .default([]),
});

/** Wizard draft — accumulated state across all steps. */
export type ProjectDraft = {
  title: string;
  abstract: string;
  objectives: string;
  methodology: string;
  expected_results: string;
  keywords: string;
  start_date: string;
  estimated_end_date: string;
  center: string;
  group: string;
  line: string;
  principal_investigator: string;
  members: TeamMemberDraft[];
  documents: DocumentDraft[];
};

/** Team member entry in the wizard draft. */
export interface TeamMemberDraft {
  researcher: string;
  role: string;
}

/** Document entry in the wizard draft. */
export interface DocumentDraft {
  name: string;
  doc_type: string;
  external_url: string;
}
