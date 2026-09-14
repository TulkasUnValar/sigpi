/**
 * Advances feature constants — Spanish labels and option lists.
 *
 * Status labels mirror the ProgressStatus choices (models.py) and the
 * StatusBadge vocabulary. Doc-type labels mirror the
 * ProgressDocumentType choices (evidence/annex/report/other).
 */

/** Spanish labels for the 6 advance FSM states. */
export const ADVANCE_STATUS_LABELS: Record<string, string> = {
  borrador: "Borrador",
  enviado: "Enviado",
  en_revision: "En revisión",
  observado: "Observado",
  aprobado: "Aprobado",
  rechazado: "Rechazado",
};

/** Advance status filter options. */
export const ADVANCE_STATUS_OPTIONS = [
  { value: "borrador", label: "Borrador" },
  { value: "enviado", label: "Enviado" },
  { value: "en_revision", label: "En revisión" },
  { value: "observado", label: "Observado" },
  { value: "aprobado", label: "Aprobado" },
  { value: "rechazado", label: "Rechazado" },
] as const;

/** Spanish labels for AdvanceDocument doc_type choices. */
export const ADVANCE_DOC_TYPE_LABELS: Record<string, string> = {
  evidence: "Evidencia",
  annex: "Anexo",
  report: "Informe",
  other: "Otro",
};

/** AdvanceDocument doc_type select options. */
export const ADVANCE_DOC_TYPE_OPTIONS = [
  { value: "evidence", label: "Evidencia" },
  { value: "annex", label: "Anexo" },
  { value: "report", label: "Informe" },
  { value: "other", label: "Otro" },
] as const;

/** Resolve an advance status value into its Spanish label (fallback: raw value). */
export function getAdvanceStatusLabel(status: string): string {
  return ADVANCE_STATUS_LABELS[status] ?? status;
}

/** Resolve a document type value into its Spanish label (fallback: raw value). */
export function getAdvanceDocTypeLabel(docType: string): string {
  return ADVANCE_DOC_TYPE_LABELS[docType] ?? docType;
}
