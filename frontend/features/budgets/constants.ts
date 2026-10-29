/**
 * Budgets feature constants — status variants, currency formatting, value arrays.
 * Labels are now in translation files (budgets.status.*, budgets.docType.*).
 */

import type { BudgetDocType, BudgetStatus } from "./types";

/** Budget status badge variants (shadcn). */
export const BUDGET_STATUS_VARIANTS: Record<BudgetStatus, "default" | "secondary" | "destructive"> = {
  draft: "secondary",
  approved: "default",
  closed: "destructive",
};

/** Budget status values for iteration. */
export const BUDGET_STATUS_VALUES: BudgetStatus[] = ["draft", "approved", "closed"];

/** Document type values for iteration. */
export const BUDGET_DOC_TYPE_VALUES: BudgetDocType[] = [
  "acta_inicio",
  "acta_comite",
  "acta_aprobacion",
  "acta_cierre",
  "formulacion",
  "informe_parcial",
  "informe_final",
  "evidencia_producto",
  "presupuesto",
  "carta_aval",
  "certificacion",
  "otro",
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
