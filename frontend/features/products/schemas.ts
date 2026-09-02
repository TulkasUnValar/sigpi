/**
 * Products form schema — zod validation mirroring the DRF serializers.
 *
 * Rules (ResearchProductSerializer):
 *   - title required.
 *   - type must be one of the 11 ProductType choices.
 *   - publication_year integer between 1900 and current_year + 1.
 *
 * buildProductPayload projects the form values onto the writable fields:
 * read-only institution/timestamps/audit fields are never sent.
 */

import { z } from "zod";

import { PRODUCT_TYPES } from "@/features/products/constants";
import type { CreateProductPayload, ProductType } from "@/features/products/types";

/** Lower bound for publication_year (backend serializer). */
export const MIN_PUBLICATION_YEAR = 1900;

/** Upper bound for publication_year: current_year + 1 (backend serializer). */
export const MAX_PUBLICATION_YEAR = new Date().getFullYear() + 1;

/** Type codes accepted by the form (the 11 ProductType choices). */
const PRODUCT_TYPE_VALUES = Object.keys(PRODUCT_TYPES) as [ProductType, ...ProductType[]];

/** Writable product form values. */
export const productFormSchema = z.object({
  project: z.string().min(1, "El proyecto es obligatorio."),
  title: z.string().min(1, "El título es obligatorio."),
  description: z.string().min(1, "La descripción es obligatoria."),
  type: z.enum(PRODUCT_TYPE_VALUES, {
    errorMap: () => ({ message: "El tipo de producto es obligatorio." }),
  }),
  publication_year: z.coerce
    .number()
    .int("El año de publicación debe ser un número entero.")
    .min(MIN_PUBLICATION_YEAR, "El año de publicación debe ser 1900 o posterior.")
    .max(MAX_PUBLICATION_YEAR, `El año de publicación no puede superar ${MAX_PUBLICATION_YEAR}.`),
});

/** Form values inferred from the schema. */
export type ProductFormValues = z.infer<typeof productFormSchema>;

/** Project form values onto the writable API payload. */
export function buildProductPayload(values: ProductFormValues): CreateProductPayload {
  return {
    project: values.project,
    title: values.title,
    description: values.description,
    type: values.type,
    publication_year: values.publication_year,
  };
}

/** Nested author schema (ProductAuthorSerializer writable fields). */
export const productAuthorSchema = z.object({
  researcher: z.string().min(1, "El investigador es obligatorio."),
  is_principal: z.boolean().default(false),
  order: z.coerce.number().int().min(0).default(0),
});

/** Nested attachment schema — metadata only, free-text doc_type ≤ 50. */
export const productAttachmentSchema = z.object({
  name: z.string().min(1, "El nombre es obligatorio."),
  doc_type: z
    .string()
    .min(1, "El tipo de documento es obligatorio.")
    .max(50, "El tipo de documento no puede superar 50 caracteres."),
  external_url: z.string().url("La URL externa debe ser válida."),
});
