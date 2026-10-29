/**
 * Project wizard step schemas — zod validation per step.
 *
 * basic → classification (center/group/line) → team → documents → review.
 * Each step has its own schema; the review step is a projection of the
 * collected data.
 */

import { z } from "zod";

import type { UpdateProjectPayload } from "@/features/projects/types";

/** Basic info step: title, abstract, objectives, methodology, dates. */
export const basicStepSchema = z
  .object({
    title: z.string().min(1, "validation.titleRequired"),
    abstract: z.string().min(1, "validation.abstractRequired"),
    objectives: z.string().min(1, "validation.objectivesRequired"),
    methodology: z.string().min(1, "validation.methodologyRequired"),
    expected_results: z.string().min(1, "validation.expectedResultsRequired"),
    keywords: z.string().optional().default(""),
    start_date: z.string().min(1, "validation.startDateRequired"),
    estimated_end_date: z.string().min(1, "validation.endDateRequired"),
  })
  .refine(
    (data) =>
      !data.start_date || !data.estimated_end_date || data.estimated_end_date >= data.start_date,
    {
      message: "validation.endDateAfterStart",
      path: ["estimated_end_date"],
    },
  );

/** Classification step: center required; group/line optional. */
export const classificationStepSchema = z.object({
  center: z.string().min(1, "validation.centerRequired"),
  group: z.string().optional().default(""),
  line: z.string().optional().default(""),
});

/** Team step: members optional, but each must have a role. */
export const teamStepSchema = z.object({
  members: z
    .array(
      z.object({
        researcher: z.string().min(1),
        role: z.string().min(1, "validation.memberRoleRequired"),
      }),
    )
    .default([]),
});

/** Document step: documents optional. */
export const documentsStepSchema = z.object({
  documents: z
    .array(
      z.object({
        name: z.string().min(1, "validation.documentNameRequired"),
        doc_type: z.string().min(1),
        external_url: z.string().min(1, "validation.documentUrlRequired"),
      }),
    )
    .default([]),
});

/**
 * ProjectForm schema — the writable scalars of an edit, validated with the
 * same rules as the create wizard (basic + classification steps).
 *
 * `group`/`line` are optional relations carried as `""` in the form; the
 * payload builder converts empty strings to `null`. The schema never
 * includes `project`, `members`, or `documents`.
 */
export const projectFormSchema = z
  .object({
    title: z.string().min(1, "validation.titleRequired"),
    abstract: z.string().min(1, "validation.abstractRequired"),
    objectives: z.string().min(1, "validation.objectivesRequired"),
    methodology: z.string().min(1, "validation.methodologyRequired"),
    expected_results: z.string().min(1, "validation.expectedResultsRequired"),
    keywords: z.string(),
    start_date: z.string().min(1, "validation.startDateRequired"),
    estimated_end_date: z.string().min(1, "validation.endDateRequired"),
    center: z.string().min(1, "validation.centerRequired"),
    group: z.string(),
    line: z.string(),
    principal_investigator: z.string().min(1, "validation.piRequired"),
  })
  .refine(
    (data) =>
      !data.start_date || !data.estimated_end_date || data.estimated_end_date >= data.start_date,
    {
      message: "validation.endDateAfterStart",
      path: ["estimated_end_date"],
    },
  );

/** Form values inferred from the edit schema. */
export type ProjectFormValues = z.infer<typeof projectFormSchema>;

/**
 * Project the form values onto the PATCH payload: only the writable scalar
 * fields, with empty `group`/`line` normalized to `null`. Read-only
 * relations (`project`, `members`, `documents`) are never included.
 */
export function buildUpdatePayload(values: ProjectFormValues): UpdateProjectPayload {
  return {
    title: values.title,
    abstract: values.abstract,
    objectives: values.objectives,
    methodology: values.methodology,
    expected_results: values.expected_results,
    keywords: values.keywords,
    start_date: values.start_date,
    estimated_end_date: values.estimated_end_date,
    center: values.center,
    group: values.group || null,
    line: values.line || null,
    principal_investigator: values.principal_investigator,
  };
}

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
