/**
 * Researchers Zod schemas — create/edit form validation.
 *
 * Spec (researchers-ui create/edit): fields match ResearcherCreateSerializer
 * writable fields. Required fields surface Spanish messages; optional text
 * fields normalize to "". `is_active` is part of the create payload and the
 * edit payload (the edit route uses the same serializer for PATCH and the
 * is_active toggle enables reactivation).
 */

import { z } from "zod";

/** Document type choices (backend DocumentTypeChoices: CC/TI/CE/PA). */
export const DOCUMENT_TYPES = ["CC", "TI", "CE", "PA"] as const;

/** Create researcher schema — mirrors ResearcherCreateSerializer. */
export const researcherCreateSchema = z.object({
  first_name: z.string().min(1, "El primer nombre es obligatorio."),
  last_name: z.string().min(1, "El apellido es obligatorio."),
  document_type: z.enum(DOCUMENT_TYPES, { message: "Seleccione un tipo de documento válido." }),
  document_number: z.string().min(1, "El número de documento es obligatorio."),
  primary_email: z
    .string()
    .email("Ingrese un correo electrónico válido.")
    .or(z.literal(""))
    .refine((v) => v !== "", { message: "El correo electrónico es obligatorio." }),
  phone: z.string().optional().default(""),
  bio: z.string().optional().default(""),
  academic_formation: z.string().optional().default(""),
  is_active: z.boolean().optional().default(true),
});

export type ResearcherCreateFormValues = z.infer<typeof researcherCreateSchema>;

/** Edit researcher schema — same writable fields (PATCH). */
export const researcherEditSchema = researcherCreateSchema;

export type ResearcherEditFormValues = z.infer<typeof researcherEditSchema>;
