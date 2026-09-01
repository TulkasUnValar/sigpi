/**
 * Seed fixtures — dev data adapter.
 *
 * Spec (cross-cutting seed data): the system MUST provide dev fixtures
 * producing non-empty dashboard, projects, and advances states.
 *
 * seedAdapter() is the single entry point for the dev flow: the MSW
 * handlers consume these fixtures so the app renders non-empty data
 * after a database reset without a real backend.
 */

import { fixtureProjects, type FixtureProject } from "@/fixtures/projects";
import {
  fixtureAdvances,
  fixtureAdvanceDetails,
  type FixtureAdvance,
  type FixtureAdvanceDetail,
} from "@/fixtures/advances";
import {
  fixtureInstitutions,
  fixtureSedes,
  fixtureFacultades,
  fixtureCenters,
  fixtureGroups,
  fixtureLines,
  type FixtureInstitution,
  type FixtureSede,
  type FixtureFacultad,
  type FixtureResearchCenter,
  type FixtureResearchGroup,
  type FixtureResearchLine,
} from "@/fixtures/institutions";
import {
  fixtureResearchers,
  fixtureResearcherDetails,
  fixtureAffiliations,
  fixtureExternalProfiles,
  fixtureAttachments,
  type FixtureResearcher,
  type FixtureResearcherList,
} from "@/fixtures/researchers";

/** Lightweight project shape consumed by the dashboard selectors. */
export interface SeedProjectSummary {
  id: string;
  title: string;
  status: string;
}

/** Lightweight advance shape consumed by the dashboard selectors. */
export interface SeedProgressSummary {
  id: string;
  project: string;
  status: string;
  cumulative_percentage: number;
}

/** Dashboard-shaped subset: project + progress summaries. */
export interface SeedDashboard {
  projects: SeedProjectSummary[];
  progress: SeedProgressSummary[];
}

/** Full seeded state for the dev flow. */
export interface SeedState {
  projects: FixtureProject[];
  advances: FixtureAdvance[];
  advanceDetails: Record<string, FixtureAdvanceDetail>;
  dashboard: SeedDashboard;
}

/** Build the dashboard-shaped subset from the fixtures. */
export function buildSeedDashboard(): SeedDashboard {
  return {
    projects: fixtureProjects.map(({ id, title, status }) => ({
      id,
      title,
      status,
    })),
    progress: fixtureAdvances.map(({ id, project, status, cumulative_percentage }) => ({
      id,
      project,
      status,
      cumulative_percentage,
    })),
  };
}

/** Single entry point: non-empty dashboard, projects, and advances. */
export function seedAdapter(): SeedState {
  return {
    projects: fixtureProjects,
    advances: fixtureAdvances,
    advanceDetails: fixtureAdvanceDetails,
    dashboard: buildSeedDashboard(),
  };
}

export { fixtureProjects, fixtureAdvances, fixtureAdvanceDetails };
export type { FixtureProject, FixtureAdvance, FixtureAdvanceDetail };
export {
  fixtureInstitutions,
  fixtureSedes,
  fixtureFacultades,
  fixtureCenters,
  fixtureGroups,
  fixtureLines,
  fixtureResearchers,
  fixtureResearcherDetails,
  fixtureAffiliations,
  fixtureExternalProfiles,
  fixtureAttachments,
};
export type {
  FixtureInstitution,
  FixtureSede,
  FixtureFacultad,
  FixtureResearchCenter,
  FixtureResearchGroup,
  FixtureResearchLine,
  FixtureResearcher,
  FixtureResearcherList,
};
