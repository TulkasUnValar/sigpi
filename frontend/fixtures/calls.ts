/**
 * Seed fixtures — calls dataset.
 *
 * Mirrors the DRF CallListSerializer (list rows) and CallSerializer
 * (full details). CALLS_FSM / CALL_ACTION_FROM_STATES drive the MSW
 * transition handlers so dev/tests behave like the backend state machine.
 */

/** Call row matching the DRF list serializer. */
export interface FixtureCall {
  id: string;
  title: string;
  status: string;
  call_type: string;
  created_at: string;
}

/** Full call detail matching the DRF CallSerializer. */
export interface FixtureCallDetail {
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

/** Non-empty call set spanning several FSM states. */
export const fixtureCalls: FixtureCall[] = [
  {
    id: "call-1",
    title: "Convocatoria IA 2026",
    status: "abierta",
    call_type: "internal",
    created_at: "2026-01-01T09:00:00Z",
  },
  {
    id: "call-2",
    title: "Convocatoria Externa 2026",
    status: "borrador",
    call_type: "external",
    created_at: "2026-01-15T09:00:00Z",
  },
  {
    id: "call-3",
    title: "Convocatoria Biotecnología",
    status: "en_evaluacion",
    call_type: "internal",
    created_at: "2025-11-20T09:00:00Z",
  },
  {
    id: "call-4",
    title: "Convocatoria Energías Renovables",
    status: "resultados_publicados",
    call_type: "internal",
    created_at: "2025-09-10T09:00:00Z",
  },
  {
    id: "call-5",
    title: "Convocatoria Ciencias Sociales",
    status: "cerrada",
    call_type: "external",
    created_at: "2025-10-05T09:00:00Z",
  },
];

/** Full detail rows keyed by call id. */
export const fixtureCallDetails: Record<string, FixtureCallDetail> = {
  "call-1": {
    id: "call-1",
    institution: "inst-1",
    title: "Convocatoria IA 2026",
    description: "Financiación de proyectos de inteligencia artificial.",
    call_type: "internal",
    external_entity: "",
    submission_start: "2026-02-01",
    submission_end: "2026-03-01",
    evaluation_start: "2026-03-15",
    evaluation_end: "2026-04-15",
    status: "abierta",
    created_at: "2026-01-01T09:00:00Z",
    updated_at: "2026-01-01T09:00:00Z",
  },
  "call-2": {
    id: "call-2",
    institution: "inst-1",
    title: "Convocatoria Externa 2026",
    description: "Convocatoria con financiación externa.",
    call_type: "external",
    external_entity: "Ministerio de Ciencia",
    submission_start: null,
    submission_end: null,
    evaluation_start: null,
    evaluation_end: null,
    status: "borrador",
    created_at: "2026-01-15T09:00:00Z",
    updated_at: "2026-01-15T09:00:00Z",
  },
  "call-3": {
    id: "call-3",
    institution: "inst-1",
    title: "Convocatoria Biotecnología",
    description: "Proyectos de biotecnología aplicada.",
    call_type: "internal",
    external_entity: "",
    submission_start: "2025-10-01",
    submission_end: "2025-11-15",
    evaluation_start: "2025-11-20",
    evaluation_end: "2025-12-20",
    status: "en_evaluacion",
    created_at: "2025-11-20T09:00:00Z",
    updated_at: "2025-12-01T09:00:00Z",
  },
};

/** FSM target states for the 5 call transitions (models.py). */
export const CALLS_FSM: Record<string, string> = {
  open_call: "abierta",
  close_call: "cerrada",
  start_evaluation: "en_evaluacion",
  publish_results: "resultados_publicados",
  archive: "archivada",
};

/** Valid source states per transition (models.py @transition sources). */
export const CALL_ACTION_FROM_STATES: Record<string, string[]> = {
  open_call: ["borrador"],
  close_call: ["abierta"],
  start_evaluation: ["cerrada"],
  publish_results: ["en_evaluacion"],
  archive: ["cerrada", "resultados_publicados"],
};

/** Nested document row matching the CallDocumentSerializer. */
export interface FixtureCallDocument {
  id: string;
  call: string;
  name: string;
  doc_type: string;
  external_url: string;
  created_at: string;
}

/** Nested project association matching the CallProjectSerializer. */
export interface FixtureCallProject {
  id: string;
  call: string;
  project: string;
  linked_at: string;
}

/** Read-only state-log row matching the CallStateLogSerializer. */
export interface FixtureCallStateLog {
  id: string;
  call: string;
  from_state: string;
  to_state: string;
  triggered_by: string | null;
  reason: string;
  created_at: string;
}

/**
 * Documents keyed by call id. `call-1` (abierta) carries metadata rows;
 * `call-2` (borrador) stays empty so the delete gate has a valid target.
 */
export const fixtureCallDocuments: Record<string, FixtureCallDocument[]> = {
  "call-1": [
    {
      id: "doc-1",
      call: "call-1",
      name: "Bases de la convocatoria",
      doc_type: "convocatoria",
      external_url: "https://example.com/bases.pdf",
      created_at: "2026-01-05T09:00:00Z",
    },
    {
      id: "doc-2",
      call: "call-1",
      name: "Anexo técnico",
      doc_type: "anexo",
      external_url: "https://example.com/anexo.pdf",
      created_at: "2026-01-06T09:00:00Z",
    },
  ],
  "call-2": [],
};

/**
 * Linked projects keyed by call id. `call-1` (abierta) already links
 * `p1` — posting `p1` again is the duplicate-association 409 precondition.
 */
export const fixtureCallProjects: Record<string, FixtureCallProject[]> = {
  "call-1": [
    {
      id: "cp-1",
      call: "call-1",
      project: "p1",
      linked_at: "2026-01-10T09:00:00Z",
    },
  ],
  "call-2": [],
};

/** Read-only state logs keyed by call id (append-only). */
export const fixtureCallStateLogs: Record<string, FixtureCallStateLog[]> = {
  "call-1": [
    {
      id: "sl-1",
      call: "call-1",
      from_state: "borrador",
      to_state: "abierta",
      triggered_by: "u1",
      reason: "Apertura oficial",
      created_at: "2026-01-02T09:00:00Z",
    },
  ],
  "call-2": [],
};
