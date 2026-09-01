/**
 * Calls feature constants — Spanish labels and option lists.
 *
 * Labels mirror the DRF choice display names (models.py) and the
 * StatusBadge vocabulary so list, filters, forms and badges agree.
 */

/** Spanish labels for the 6 FSM states. */
export const CALL_STATUS_LABELS: Record<string, string> = {
  borrador: "Borrador",
  abierta: "Abierta",
  cerrada: "Cerrada",
  en_evaluacion: "En evaluación",
  resultados_publicados: "Resultados publicados",
  archivada: "Archivada",
};

/** Spanish labels for the call types. */
export const CALL_TYPE_LABELS: Record<string, string> = {
  internal: "Interna",
  external: "Externa",
};

/** Call type select options. */
export const CALL_TYPE_OPTIONS = [
  { value: "internal", label: "Interna" },
  { value: "external", label: "Externa" },
] as const;

/** Call status filter options. */
export const CALL_STATUS_OPTIONS = [
  { value: "borrador", label: "Borrador" },
  { value: "abierta", label: "Abierta" },
  { value: "cerrada", label: "Cerrada" },
  { value: "en_evaluacion", label: "En evaluación" },
  { value: "resultados_publicados", label: "Resultados publicados" },
  { value: "archivada", label: "Archivada" },
] as const;

/** Spanish labels for CallDocument doc_type choices. */
export const CALL_DOC_TYPE_LABELS: Record<string, string> = {
  convocatoria: "Convocatoria",
  anexo: "Anexo",
  reglamento: "Reglamento",
  resultado: "Resultado",
  otro: "Otro",
};

/** CallDocument doc_type select options. */
export const CALL_DOC_TYPE_OPTIONS = [
  { value: "convocatoria", label: "Convocatoria" },
  { value: "anexo", label: "Anexo" },
  { value: "reglamento", label: "Reglamento" },
  { value: "resultado", label: "Resultado" },
  { value: "otro", label: "Otro" },
] as const;

/** Resolve a call type value into its Spanish label (fallback: raw value). */
export function getCallTypeLabel(callType: string): string {
  return CALL_TYPE_LABELS[callType] ?? callType;
}

/** Resolve a call status value into its Spanish label (fallback: raw value). */
export function getCallStatusLabel(status: string): string {
  return CALL_STATUS_LABELS[status] ?? status;
}
