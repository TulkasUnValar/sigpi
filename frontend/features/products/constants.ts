/**
 * Products feature constants — type codes and allowed project states.
 *
 * Labels are resolved via next-intl translations (products.types namespace).
 * ALLOWED_PROJECT_STATES mirrors the backend guard PRODUCT_ALLOWED_PROJECT_STATES (views.py).
 */

/** Product type codes matching DRF ProductType choices (models.py). */
export const PRODUCT_TYPE_CODES = [
  "articulo",
  "libro",
  "capitulo",
  "software",
  "prototipo",
  "evento",
  "consultoria",
  "diseno_industrial",
  "innovacion_proceso",
  "innovacion_gestion",
  "carta",
] as const;

export type ProductTypeCode = (typeof PRODUCT_TYPE_CODES)[number];

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

/** Type for next-intl translation function. */
type TranslationFn = (key: string) => string;

/**
 * Build product type select options using the provided translation function.
 * Options follow the same order as the backend choices.
 */
export function getProductTypeOptions(t: TranslationFn): Array<{ value: string; label: string }> {
  return PRODUCT_TYPE_CODES.map((code) => ({
    value: code,
    label: t(`types.${code}`),
  }));
}

/** Resolve a product type code into its translated label (fallback: raw value). */
export function getProductTypeLabel(t: TranslationFn, type: string): string {
  try {
    const label = t(`types.${type}`);
    return label ?? type;
  } catch {
    return type;
  }
}
