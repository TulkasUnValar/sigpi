/**
 * Budgets feature constants — Spanish labels, status mappings, doc types.
 */

import type { BudgetDocType, BudgetStatus } from "./types";

/** Budget status Spanish labels. */
export const BUDGET_STATUS_LABELS: Record<BudgetStatus, string> = {
  draft: "Borrador",
  approved: "Aprobado",
  closed: "Cerrado",
};

/** Budget status badge variants (shadcn). */
export const BUDGET_STATUS_VARIANTS: Record<BudgetStatus, "default" | "secondary" | "destructive"> = {
  draft: "secondary",
  approved: "default",
  closed: "destructive",
};

/** Document type Spanish labels. */
export const BUDGET_DOC_TYPE_LABELS: Record<BudgetDocType, string> = {
  acta_inicio: "Acta de inicio",
  acta_comite: "Acta de comité",
  acta_aprobacion: "Acta de aprobación",
  acta_cierre: "Acta de cierre",
  formulacion: "Formulación del proyecto",
  informe_parcial: "Informe parcial",
  informe_final: "Informe final",
  evidencia_producto: "Evidencia de producto",
  presupuesto: "Presupuesto",
  carta_aval: "Carta o aval",
  certificacion: "Certificación",
  otro: "Otro",
};

/** Document type options for select inputs. */
export const BUDGET_DOC_TYPE_OPTIONS = Object.entries(BUDGET_DOC_TYPE_LABELS).map(
  ([value, label]) => ({
    value: value as BudgetDocType,
    label,
  })
);

/** Budget status options for filters. */
export const BUDGET_STATUS_OPTIONS: { value: BudgetStatus; label: string }[] = [
  { value: "draft", label: "Borrador" },
  { value: "approved", label: "Aprobado" },
  { value: "closed", label: "Cerrado" },
];

/** Currency formatter for COP. */
export const formatCurrency = (amount: string | number): string => {
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
};

/** Parse decimal string to number for calculations. */
export const parseDecimal = (value: string): number => {
  return parseFloat(value) || 0;
};
