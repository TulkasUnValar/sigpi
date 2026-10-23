/**
 * Budgets feature types — mirror the DRF serializers (apps/budgets).
 *
 * - Budget: full serializer with nested lines and attachments.
 * - BudgetLine: rubro with approved_amount.
 * - FundingSource: source linked to project.
 * - BudgetExecution: execution record with authorization fields.
 * - BudgetAttachment: metadata-only attachment.
 * - BudgetSummary: approved/executed/balance indicators.
 * - Page<T>: DRF paginated envelope.
 */

/** DRF paginated envelope. */
export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/** Budget status choices. */
export type BudgetStatus = "draft" | "approved" | "closed";

/** Document type choices for attachments. */
export type BudgetDocType =
  | "acta_inicio"
  | "acta_comite"
  | "acta_aprobacion"
  | "acta_cierre"
  | "formulacion"
  | "informe_parcial"
  | "informe_final"
  | "evidencia_producto"
  | "presupuesto"
  | "carta_aval"
  | "certificacion"
  | "otro";

/** Budget detail (BudgetSerializer). */
export interface Budget {
  id: string;
  project: string;
  institution: string;
  name: string;
  approved_amount: string;
  status: BudgetStatus;
  lines: BudgetLine[];
  attachments: BudgetAttachment[];
  created_at: string;
  updated_at: string;
}

/** Budget list item (lightweight). */
export interface BudgetListItem {
  id: string;
  project: string;
  project_name: string;
  name: string;
  approved_amount: string;
  status: BudgetStatus;
  created_at: string;
}

/** Budget line (rubro) — BudgetLineSerializer. */
export interface BudgetLine {
  id: string;
  budget: string;
  name: string;
  approved_amount: string;
  created_at: string;
  updated_at: string;
}

/** Funding source — FundingSourceSerializer. */
export interface FundingSource {
  id: string;
  project: string;
  name: string;
  amount: string;
  created_at: string;
  updated_at: string;
}

/** Budget execution — BudgetExecutionSerializer. */
export interface BudgetExecution {
  id: string;
  line: string;
  amount: string;
  executed_at: string;
  authorized_by: string | null;
  authorized_at: string | null;
  created_at: string;
  updated_at: string;
}

/** Budget attachment (metadata-only) — BudgetAttachmentSerializer. */
export interface BudgetAttachment {
  id: string;
  budget: string;
  name: string;
  doc_type: BudgetDocType;
  external_url: string;
  created_at: string;
}

/** Summary indicators (IND-007/008/009). */
export interface BudgetSummary {
  approved: string;
  executed: string;
  balance: string;
}

/** List filters supported by BudgetFilter. */
export interface BudgetFilter {
  project?: string;
  status?: BudgetStatus;
}

/** Writable payload for POST /budgets/. */
export interface CreateBudgetPayload {
  project: string;
  name: string;
  approved_amount: string;
}

/** Writable payload for PATCH /budgets/{id}/. */
export interface UpdateBudgetPayload {
  name?: string;
  approved_amount?: string;
}

/** Writable payload for POST /budgets/{id}/lines/. */
export interface CreateBudgetLinePayload {
  name: string;
  approved_amount: string;
}

/** Writable payload for PATCH /budgets/{id}/lines/{lid}/. */
export interface UpdateBudgetLinePayload {
  name?: string;
  approved_amount?: string;
}

/** Writable payload for POST /projects/{pid}/funding-sources/. */
export interface CreateFundingSourcePayload {
  name: string;
  amount: string;
}

/** Writable payload for PATCH /projects/{pid}/funding-sources/{sid}/. */
export interface UpdateFundingSourcePayload {
  name?: string;
  amount?: string;
}

/** Writable payload for POST /budgets/{id}/lines/{lid}/executions/. */
export interface CreateBudgetExecutionPayload {
  amount: string;
  executed_at: string;
  authorized_by?: string | null;
  authorized_at?: string | null;
}

/** Writable payload for POST /budgets/{id}/attachments/. */
export interface CreateBudgetAttachmentPayload {
  name: string;
  doc_type: BudgetDocType;
  external_url: string;
}

/** Writable payload for PATCH /budgets/{id}/attachments/{aid}/. */
export interface UpdateBudgetAttachmentPayload {
  name?: string;
  doc_type?: BudgetDocType;
  external_url?: string;
}
