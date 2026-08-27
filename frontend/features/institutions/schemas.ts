/**
 * Institutions Zod schemas — one schema per entity level.
 *
 * The institution schema drives the EntityForm (RHF + zodResolver).
 * Contact fields are optional but validated when provided. Child entity
 * schemas keep the parent relation OUT of the body (parent ids come from
 * the URL) — only optional references are selectable.
 */

import { z } from "zod";

import type { EntityConfig } from "@/features/institutions/types";

/** Institution create/edit form schema (RF-F02). */
export const institutionSchema = z.object({
  name: z.string().min(1, "El nombre es obligatorio."),
  code: z
    .string()
    .min(1, "El código es obligatorio.")
    .max(20, "El código no puede superar 20 caracteres."),
  description: z.string().optional().default(""),
  address: z.string().optional().default(""),
  contact_email: z
    .string()
    .email("Ingrese un correo electrónico válido.")
    .or(z.literal(""))
    .optional()
    .default(""),
  contact_phone: z.string().optional().default(""),
  logo_url: z.string().url("Ingrese una URL válida.").or(z.literal("")).optional().default(""),
});

export type InstitutionFormValues = z.infer<typeof institutionSchema>;

/** Sede form schema (basic fields; parent from URL). */
export const sedeSchema = z.object({
  code: z
    .string()
    .min(1, "El código es obligatorio.")
    .max(20, "El código no puede superar 20 caracteres."),
  name: z.string().min(1, "El nombre es obligatorio."),
  description: z.string().optional().default(""),
});

/** Facultad form schema — optional sede reference. */
export const facultadSchema = z.object({
  sede: z.string().optional().default(""),
  code: z
    .string()
    .min(1, "El código es obligatorio.")
    .max(20, "El código no puede superar 20 caracteres."),
  name: z.string().min(1, "El nombre es obligatorio."),
  description: z.string().optional().default(""),
});

/** ResearchCenter form schema — optional sede/facultad + contact fields. */
export const centerSchema = z.object({
  sede: z.string().optional().default(""),
  facultad: z.string().optional().default(""),
  code: z
    .string()
    .min(1, "El código es obligatorio.")
    .max(20, "El código no puede superar 20 caracteres."),
  name: z.string().min(1, "El nombre es obligatorio."),
  description: z.string().optional().default(""),
  contact_email: z
    .string()
    .email("Ingrese un correo electrónico válido.")
    .or(z.literal(""))
    .optional()
    .default(""),
  contact_phone: z.string().optional().default(""),
});

/** ResearchGroup form schema (basic fields). */
export const groupSchema = z.object({
  code: z
    .string()
    .min(1, "El código es obligatorio.")
    .max(20, "El código no puede superar 20 caracteres."),
  name: z.string().min(1, "El nombre es obligatorio."),
  description: z.string().optional().default(""),
});

/** ResearchLine form schema (basic fields). */
export const lineSchema = z.object({
  code: z
    .string()
    .min(1, "El código es obligatorio.")
    .max(20, "El código no puede superar 20 caracteres."),
  name: z.string().min(1, "El nombre es obligatorio."),
  description: z.string().optional().default(""),
});

/**
 * Institution entity config — drives EntityForm fields, endpoints and
 * the write-role threshold (backend: IsSuperAdmin).
 */
export const institutionConfig: EntityConfig<InstitutionFormValues> = {
  kind: "institution",
  label: "Institución",
  pluralLabel: "Instituciones",
  listPath: "/api/institutions/",
  detailPath: (id) => `/api/institutions/${id}/`,
  fsmPath: (id, action) => `/api/institutions/${id}/${action}/`,
  schema: institutionSchema,
  fields: [
    { name: "name", label: "Nombre", type: "text" },
    { name: "code", label: "Código", type: "text" },
    { name: "description", label: "Descripción", type: "textarea" },
    { name: "address", label: "Dirección", type: "textarea" },
    { name: "contact_email", label: "Correo de contacto", type: "email" },
    { name: "contact_phone", label: "Teléfono de contacto", type: "text" },
    { name: "logo_url", label: "URL del logo", type: "url" },
  ],
  minRoles: ["superadmin"],
  isRoot: true,
};
