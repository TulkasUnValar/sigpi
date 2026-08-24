/**
 * Seed fixtures — advances (progress reports) dataset.
 *
 * Spec (cross-cutting seed data): dev fixtures producing non-empty
 * dashboard, projects, and advances states after a database reset.
 *
 * Advances reference fixture projects by id; each detail carries nested
 * reviews and state logs so the detail route renders fully.
 */

/** Advance row matching the DRF ProgressReportListSerializer. */
export interface FixtureAdvance {
  id: string;
  project: string;
  status: string;
  cumulative_percentage: number;
  period_start: string;
  period_end: string;
  created_at: string;
}

/** Advance detail matching the full ProgressReportSerializer. */
export interface FixtureAdvanceDetail extends FixtureAdvance {
  institution: string;
  created_by: string;
  description: string;
  activities: string;
  difficulties: string;
  next_steps: string;
  updated_at: string;
  documents: {
    id: string;
    progress_report: string;
    name: string;
    doc_type: string;
    external_url: string;
    uploaded_at: string;
  }[];
  reviews: {
    id: string;
    progress_report: string;
    reviewed_by: string | null;
    review_text: string;
    review_type: string;
    created_at: string;
  }[];
  state_logs: {
    id: string;
    progress_report: string;
    from_state: string;
    to_state: string;
    triggered_by: string | null;
    reason: string;
    created_at: string;
  }[];
}

/** Non-empty advance set — en_revision (director queue) and aprobado. */
export const fixtureAdvances: FixtureAdvance[] = [
  {
    id: "a1",
    project: "p3",
    status: "en_revision",
    cumulative_percentage: 30,
    period_start: "2026-04-01",
    period_end: "2026-06-30",
    created_at: "2026-04-01T00:00:00Z",
  },
  {
    id: "a2",
    project: "p3",
    status: "aprobado",
    cumulative_percentage: 50,
    period_start: "2026-01-01",
    period_end: "2026-03-31",
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "a3",
    project: "p4",
    status: "en_revision",
    cumulative_percentage: 15,
    period_start: "2026-04-01",
    period_end: "2026-06-30",
    created_at: "2026-04-15T00:00:00Z",
  },
];

/** Full details keyed by advance id (nested reviews + state logs). */
export const fixtureAdvanceDetails: Record<string, FixtureAdvanceDetail> = {
  a1: {
    id: "a1",
    project: "p3",
    status: "en_revision",
    cumulative_percentage: 30,
    period_start: "2026-04-01",
    period_end: "2026-06-30",
    created_at: "2026-04-01T00:00:00Z",
    institution: "inst-1",
    created_by: "r2",
    description: "Avance del segundo trimestre del Proyecto Gamma.",
    activities: "Recolección de datos de campo; análisis preliminar.",
    difficulties: "Acceso limitado a laboratorio.",
    next_steps: "Procesar muestras y presentar resultados parciales.",
    updated_at: "2026-05-01T00:00:00Z",
    documents: [
      {
        id: "d1",
        progress_report: "a1",
        name: "Registro de datos.xlsx",
        doc_type: "evidence",
        external_url: "https://example.com/d1",
        uploaded_at: "2026-04-10T00:00:00Z",
      },
    ],
    reviews: [
      {
        id: "r1",
        progress_report: "a1",
        reviewed_by: "u2",
        review_text: "Falta justificar el tamaño de la muestra.",
        review_type: "observation",
        created_at: "2026-05-02T00:00:00Z",
      },
    ],
    state_logs: [
      {
        id: "s1",
        progress_report: "a1",
        from_state: "borrador",
        to_state: "enviado",
        triggered_by: "r2",
        reason: "",
        created_at: "2026-04-01T00:00:00Z",
      },
      {
        id: "s2",
        progress_report: "a1",
        from_state: "enviado",
        to_state: "en_revision",
        triggered_by: "u2",
        reason: "",
        created_at: "2026-04-02T00:00:00Z",
      },
    ],
  },
  a2: {
    id: "a2",
    project: "p3",
    status: "aprobado",
    cumulative_percentage: 50,
    period_start: "2026-01-01",
    period_end: "2026-03-31",
    created_at: "2026-01-01T00:00:00Z",
    institution: "inst-1",
    created_by: "r2",
    description: "Avance del primer trimestre del Proyecto Gamma.",
    activities: "Diseño metodológico y revisión bibliográfica.",
    difficulties: "",
    next_steps: "Iniciar trabajo de campo.",
    updated_at: "2026-03-01T00:00:00Z",
    documents: [],
    reviews: [],
    state_logs: [
      {
        id: "s3",
        progress_report: "a2",
        from_state: "en_revision",
        to_state: "aprobado",
        triggered_by: "u2",
        reason: "",
        created_at: "2026-03-01T00:00:00Z",
      },
    ],
  },
  a3: {
    id: "a3",
    project: "p4",
    status: "en_revision",
    cumulative_percentage: 15,
    period_start: "2026-04-01",
    period_end: "2026-06-30",
    created_at: "2026-04-15T00:00:00Z",
    institution: "inst-1",
    created_by: "r2",
    description: "Primer avance del Proyecto Delta.",
    activities: "Configuración del entorno experimental.",
    difficulties: "Equipamiento pendiente de entrega.",
    next_steps: "Iniciar mediciones.",
    updated_at: "2026-05-01T00:00:00Z",
    documents: [],
    reviews: [],
    state_logs: [
      {
        id: "s4",
        progress_report: "a3",
        from_state: "borrador",
        to_state: "enviado",
        triggered_by: "r2",
        reason: "",
        created_at: "2026-04-15T00:00:00Z",
      },
      {
        id: "s5",
        progress_report: "a3",
        from_state: "enviado",
        to_state: "en_revision",
        triggered_by: "u2",
        reason: "",
        created_at: "2026-04-16T00:00:00Z",
      },
    ],
  },
};