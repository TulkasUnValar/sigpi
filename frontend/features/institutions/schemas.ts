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

export type SedeFormValues = z.infer<typeof sedeSchema>;

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

export type FacultadFormValues = z.infer<typeof facultadSchema>;

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

export type CenterFormValues = z.infer<typeof centerSchema>;

/** ResearchGroup form schema (basic fields; parent center from URL). */
export const groupSchema = z.object({
  code: z
    .string()
    .min(1, "El código es obligatorio.")
    .max(20, "El código no puede superar 20 caracteres."),
  name: z.string().min(1, "El nombre es obligatorio."),
  description: z.string().optional().default(""),
});

export type GroupFormValues = z.infer<typeof groupSchema>;

/** ResearchLine form schema (basic fields; parent group from URL). */
export const lineSchema = z.object({
  code: z
    .string()
    .min(1, "El código es obligatorio.")
    .max(20, "El código no puede superar 20 caracteres."),
  name: z.string().min(1, "El nombre es obligatorio."),
  description: z.string().optional().default(""),
});

export type LineFormValues = z.infer<typeof lineSchema>;

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

/**
 * Sede entity config — child of an institution (parent from URL).
 * Write threshold: admin or superadmin (RF-F05).
 */
export const sedeConfig: EntityConfig<SedeFormValues> = {
  kind: "sede",
  label: "Sede",
  pluralLabel: "Sedes",
  listPath: "/api/institutions/{pk}/sedes/",
  detailPath: (id) => `/api/sedes/${id}/`,
  fsmPath: (id, action) => `/api/sedes/${id}/${action}/`,
  schema: sedeSchema,
  fields: [
    { name: "code", label: "Código", type: "text" },
    { name: "name", label: "Nombre", type: "text" },
    { name: "description", label: "Descripción", type: "textarea" },
  ],
  minRoles: ["admin", "superadmin"],
};

/**
 * Facultad entity config — child of an institution with an optional sede
 * reference. Write threshold: admin or superadmin (RF-F05).
 */
export const facultadConfig: EntityConfig<FacultadFormValues> = {
  kind: "facultad",
  label: "Facultad",
  pluralLabel: "Facultades",
  listPath: "/api/institutions/{pk}/facultades/",
  detailPath: (id) => `/api/facultades/${id}/`,
  fsmPath: (id, action) => `/api/facultades/${id}/${action}/`,
  schema: facultadSchema,
  fields: [
    { name: "sede", label: "Sede", type: "select" },
    { name: "code", label: "Código", type: "text" },
    { name: "name", label: "Nombre", type: "text" },
    { name: "description", label: "Descripción", type: "textarea" },
  ],
  minRoles: ["admin", "superadmin"],
};

/**
 * ResearchCenter entity config — child of an institution; parent_type may
 * be institution | sede | facultad (backend supports all three). The sede
 * and facultad selects are optional references, never the parent.
 * Write threshold: admin or superadmin (RF-F05).
 */
export const centerConfig: EntityConfig<CenterFormValues> = {
  kind: "center",
  label: "Centro de investigación",
  pluralLabel: "Centros de investigación",
  listPath: "/api/institutions/{pk}/centers/",
  detailPath: (id) => `/api/centers/${id}/`,
  fsmPath: (id, action) => `/api/centers/${id}/${action}/`,
  schema: centerSchema,
  fields: [
    { name: "sede", label: "Sede", type: "select" },
    { name: "facultad", label: "Facultad", type: "select" },
    { name: "code", label: "Código", type: "text" },
    { name: "name", label: "Nombre", type: "text" },
    { name: "description", label: "Descripción", type: "textarea" },
    { name: "contact_email", label: "Correo de contacto", type: "email" },
    { name: "contact_phone", label: "Teléfono de contacto", type: "text" },
  ],
  minRoles: ["admin", "superadmin"],
};

/**
 * ResearchGroup entity config — child of a center (parent from URL).
 * Write threshold: director, admin or superadmin (RF-F05).
 */
export const groupConfig: EntityConfig<GroupFormValues> = {
  kind: "group",
  label: "Grupo de investigación",
  pluralLabel: "Grupos de investigación",
  listPath: "/api/centers/{pk}/groups/",
  detailPath: (id) => `/api/groups/${id}/`,
  fsmPath: (id, action) => `/api/groups/${id}/${action}/`,
  schema: groupSchema,
  fields: [
    { name: "code", label: "Código", type: "text" },
    { name: "name", label: "Nombre", type: "text" },
    { name: "description", label: "Descripción", type: "textarea" },
  ],
  minRoles: ["director", "admin", "superadmin"],
};

/**
 * ResearchLine entity config — child of a group (parent from URL).
 * Leaf level. Write threshold: director, admin or superadmin (RF-F05).
 */
export const lineConfig: EntityConfig<LineFormValues> = {
  kind: "line",
  label: "Línea de investigación",
  pluralLabel: "Líneas de investigación",
  listPath: "/api/groups/{pk}/lines/",
  detailPath: (id) => `/api/lines/${id}/`,
  fsmPath: (id, action) => `/api/lines/${id}/${action}/`,
  schema: lineSchema,
  fields: [
    { name: "code", label: "Código", type: "text" },
    { name: "name", label: "Nombre", type: "text" },
    { name: "description", label: "Descripción", type: "textarea" },
  ],
  minRoles: ["director", "admin", "superadmin"],
};
