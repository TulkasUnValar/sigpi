/**
 * Budgets form schemas — zod validation mirroring the DRF serializers.
 *
 * Rules:
 *   - name: required, min 1 char
 *   - approved_amount: required, must be valid decimal >= 0
 *   - project: required UUID
 *   - Lines: name required, approved_amount must be valid decimal >= 0
 *   - Funding sources: name required, amount must be valid decimal >= 0
 *   - Executions: amount required >= 0, executed_at required (date)
 *   - Attachments: name required, doc_type required, external_url required (URL)
 */

import { z } from "zod";

import type {
  CreateBudgetAttachmentPayload,
  CreateBudgetExecutionPayload,
  CreateBudgetLinePayload,
  CreateBudgetPayload,
  CreateFundingSourcePayload,
  UpdateBudgetLinePayload,
  UpdateBudgetPayload,
  UpdateFundingSourcePayload,
} from "@/features/budgets/types";

// ─────────────────────────────────────────────────────────
// Decimal validation helper
// ─────────────────────────────────────────────────────────

const decimalString = z
  .string()
  .min(1, "El monto es obligatorio.")
  .refine((val) => !isNaN(parseFloat(val)), "Debe ser un número válido.")
  .refine((val) => parseFloat(val) >= 0, "El monto no puede ser negativo.");

// ─────────────────────────────────────────────────────────
// Budget form schema (create/edit)
// ─────────────────────────────────────────────────────────

export const budgetFormSchema = z.object({
  project: z.string().min(1, "El proyecto es obligatorio."),
  name: z.string().min(1, "El nombre es obligatorio."),
  approved_amount: decimalString,
});

export type BudgetFormValues = z.infer<typeof budgetFormSchema>;

/**
 * Project form values onto the writable API payload.
 * - Read-only fields (institution, status, timestamps) never included.
 */
export function buildCreateBudgetPayload(values: BudgetFormValues): CreateBudgetPayload {
  return {
    project: values.project,
    name: values.name,
    approved_amount: values.approved_amount,
  };
}

export function buildUpdateBudgetPayload(values: Partial<BudgetFormValues>): UpdateBudgetPayload {
  const payload: UpdateBudgetPayload = {};
  if (values.name !== undefined) payload.name = values.name;
  if (values.approved_amount !== undefined) payload.approved_amount = values.approved_amount;
  return payload;
}

// ─────────────────────────────────────────────────────────
// Budget line schema (create/edit)
// ─────────────────────────────────────────────────────────

export const budgetLineFormSchema = z.object({
  name: z.string().min(1, "El nombre del rubro es obligatorio."),
  approved_amount: decimalString,
});

export type BudgetLineFormValues = z.infer<typeof budgetLineFormSchema>;

export function buildCreateBudgetLinePayload(values: BudgetLineFormValues): CreateBudgetLinePayload {
  return {
    name: values.name,
    approved_amount: values.approved_amount,
  };
}

export function buildUpdateBudgetLinePayload(
  values: Partial<BudgetLineFormValues>
): UpdateBudgetLinePayload {
  const payload: UpdateBudgetLinePayload = {};
  if (values.name !== undefined) payload.name = values.name;
  if (values.approved_amount !== undefined) payload.approved_amount = values.approved_amount;
  return payload;
}

// ─────────────────────────────────────────────────────────
// Funding source schema (create/edit)
// ─────────────────────────────────────────────────────────

export const fundingSourceFormSchema = z.object({
  name: z.string().min(1, "El nombre de la fuente es obligatorio."),
  amount: decimalString,
});

export type FundingSourceFormValues = z.infer<typeof fundingSourceFormSchema>;

export function buildCreateFundingSourcePayload(
  values: FundingSourceFormValues
): CreateFundingSourcePayload {
  return {
    name: values.name,
    amount: values.amount,
  };
}

export function buildUpdateFundingSourcePayload(
  values: Partial<FundingSourceFormValues>
): UpdateFundingSourcePayload {
  const payload: UpdateFundingSourcePayload = {};
  if (values.name !== undefined) payload.name = values.name;
  if (values.amount !== undefined) payload.amount = values.amount;
  return payload;
}

// ─────────────────────────────────────────────────────────
// Budget execution schema (create)
// ─────────────────────────────────────────────────────────

export const budgetExecutionFormSchema = z.object({
  amount: decimalString,
  executed_at: z.string().min(1, "La fecha de ejecución es obligatoria."),
  authorized_by: z.string().optional().nullable(),
  authorized_at: z.string().optional().nullable(),
});

export type BudgetExecutionFormValues = z.infer<typeof budgetExecutionFormSchema>;

export function buildCreateBudgetExecutionPayload(
  values: BudgetExecutionFormValues
): CreateBudgetExecutionPayload {
  return {
    amount: values.amount,
    executed_at: values.executed_at,
    authorized_by: values.authorized_by ?? null,
    authorized_at: values.authorized_at ?? null,
  };
}

// ─────────────────────────────────────────────────────────
// Budget attachment schema (create/edit)
// ─────────────────────────────────────────────────────────

const DOC_TYPES = [
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
] as const;

export const budgetAttachmentFormSchema = z.object({
  name: z.string().min(1, "El nombre es obligatorio."),
  doc_type: z.enum(DOC_TYPES, {
    errorMap: () => ({ message: "El tipo de documento es obligatorio." }),
  }),
  external_url: z.string().url("Debe ser una URL válida.").min(1, "La URL es obligatoria."),
});

export type BudgetAttachmentFormValues = z.infer<typeof budgetAttachmentFormSchema>;

export function buildCreateBudgetAttachmentPayload(
  values: BudgetAttachmentFormValues
): CreateBudgetAttachmentPayload {
  return {
    name: values.name,
    doc_type: values.doc_type,
    external_url: values.external_url,
  };
}
