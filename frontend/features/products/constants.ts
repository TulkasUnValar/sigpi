/**
 * Products feature constants — Spanish labels and option lists.
 *
 * Labels mirror the DRF ProductType choices (models.py) so list rows,
 * filters, badges and forms agree. ALLOWED_PROJECT_STATES mirrors the
 * backend guard PRODUCT_ALLOWED_PROJECT_STATES (views.py).
 */

/** Spanish labels for the 11 product type codes. */
export const PRODUCT_TYPES: Record<string, string> = {
  articulo: "Artículo",
  libro: "Libro",
  capitulo: "Capítulo",
  software: "Software",
  prototipo: "Prototipo",
  evento: "Evento",
  consultoria: "Consultoría",
  diseno_industrial: "Diseño Industrial",
  innovacion_proceso: "Innovación de Proceso",
  innovacion_gestion: "Innovación de Gestión",
  carta: "Carta",
};

/** Product type select options (same order as the backend choices). */
export const PRODUCT_TYPE_OPTIONS = Object.entries(PRODUCT_TYPES).map(([value, label]) => ({
  value,
  label,
}));

/**
 * Project states allowed for product linking (backend views.py guard).
 * The create/edit project select is filtered client-side to these states.
 */
export const ALLOWED_PROJECT_STATES = [
  "aprobado",
  "en_ejecucion",
  "suspendido",
  "finalizado",
  "en_cierre",
  "cerrado",
] as const;

/** Resolve a product type value into its Spanish label (fallback: raw value). */
export function getProductTypeLabel(type: string): string {
  return PRODUCT_TYPES[type] ?? type;
}
