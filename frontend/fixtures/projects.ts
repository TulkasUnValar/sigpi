/**
 * Seed fixtures — projects dataset.
 *
 * Spec (cross-cutting seed data): dev fixtures producing non-empty
 * dashboard, projects, and advances states after a database reset.
 *
 * These mirror the DRF ProjectListSerializer fields so the MSW handlers
 * and the seed adapter can serve them directly.
 */

/** Project row matching the DRF list serializer (subset of ProjectDetail). */
export interface FixtureProject {
  id: string;
  title: string;
  status: string;
  center: string;
  principal_investigator: string;
  start_date: string;
  created_at: string;
}

/** Non-empty project set spanning several FSM states. */
export const fixtureProjects: FixtureProject[] = [
  {
    id: "p1",
    title: "Proyecto Alpha",
    status: "en_revision",
    center: "c1",
    principal_investigator: "r1",
    start_date: "2026-01-10",
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "p2",
    title: "Proyecto Beta",
    status: "en_revision",
    center: "c1",
    principal_investigator: "r1",
    start_date: "2026-02-01",
    created_at: "2026-01-15T00:00:00Z",
  },
  {
    id: "p3",
    title: "Proyecto Gamma",
    status: "aprobado",
    center: "c2",
    principal_investigator: "r2",
    start_date: "2026-01-20",
    created_at: "2026-01-10T00:00:00Z",
  },
  {
    id: "p4",
    title: "Proyecto Delta",
    status: "en_ejecucion",
    center: "c2",
    principal_investigator: "r2",
    start_date: "2026-03-01",
    created_at: "2026-02-01T00:00:00Z",
  },
];