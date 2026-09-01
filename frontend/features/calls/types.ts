/**
 * Calls feature types — mirror the DRF serializers (apps/calls).
 *
 * - CallList: 5-field list serializer.
 * - Call: full serializer with nullable dates (read + write).
 * - CallDocument / CallProject / CallStateLog: nested resources.
 * - Page<T>: DRF paginated envelope.
 */

/** DRF paginated envelope. */
export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/** Call FSM states (6). */
export type CallStatus =
  | "borrador"
  | "abierta"
  | "cerrada"
  | "en_evaluacion"
  | "resultados_publicados"
  | "archivada";

/** Call scope choices. */
export type CallType = "internal" | "external";

/** Lightweight call from GET /calls/ (CallListSerializer). */
export interface CallList {
  id: string;
  title: string;
  status: string;
  call_type: string;
  created_at: string;
}

/** Full call detail (CallSerializer). */
export interface Call {
  id: string;
  institution: string;
  title: string;
  description: string;
  call_type: string;
  external_entity: string;
  submission_start: string | null;
  submission_end: string | null;
  evaluation_start: string | null;
  evaluation_end: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

/** Metadata-only document record (CallDocumentSerializer). */
export interface CallDocument {
  id: string;
  call: string;
  name: string;
  doc_type: string;
  external_url: string;
  created_at: string;
}

/** Project association (CallProjectSerializer). */
export interface CallProject {
  id: string;
  call: string;
  project: string;
  linked_at: string;
}

/** State-history entry (CallStateLogSerializer). */
export interface CallStateLog {
  id: string;
  call: string;
  from_state: string;
  to_state: string;
  triggered_by: string | null;
  reason: string;
  created_at: string;
}

/** List filters supported by CallFilter (status + call_type). */
export interface CallFilter {
  status?: string;
  call_type?: string;
}

/** Writable payload for POST /calls/ (read-only fields omitted). */
export interface CreateCallPayload {
  title: string;
  description: string;
  call_type: CallType;
  external_entity?: string;
  submission_start?: string | null;
  submission_end?: string | null;
  evaluation_start?: string | null;
  evaluation_end?: string | null;
}
