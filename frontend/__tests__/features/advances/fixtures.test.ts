/**
 * Seed fixtures — dev data adapter producing non-empty dashboard, projects,
 * and advances states.
 *
 * Spec (cross-cutting seed data):
 *   GIVEN dev database reset
 *   WHEN seeding
 *   THEN dashboard, projects, advances show data.
 */

import {
  fixtureProjects,
  fixtureAdvances,
  fixtureAdvanceDetails,
  buildSeedDashboard,
  seedAdapter,
} from "@/fixtures";

describe("fixtures — non-empty datasets", () => {
  it("provides non-empty projects", () => {
    expect(fixtureProjects.length).toBeGreaterThan(0);
    fixtureProjects.forEach((p) => {
      expect(p.id).toBeTruthy();
      expect(p.title).toBeTruthy();
      expect(p.status).toBeTruthy();
    });
  });

  it("provides non-empty advances referencing known projects", () => {
    expect(fixtureAdvances.length).toBeGreaterThan(0);
    const projectIds = new Set(fixtureProjects.map((p) => p.id));
    fixtureAdvances.forEach((a) => {
      expect(a.id).toBeTruthy();
      expect(a.status).toBeTruthy();
      expect(projectIds.has(a.project)).toBe(true);
      expect(a.cumulative_percentage).toBeGreaterThanOrEqual(0);
      expect(a.cumulative_percentage).toBeLessThanOrEqual(100);
    });
  });

  it("provides full advance details with reviews and state history", () => {
    expect(Object.keys(fixtureAdvanceDetails).length).toBeGreaterThan(0);
    Object.values(fixtureAdvanceDetails).forEach((d) => {
      expect(d.description).toBeTruthy();
      expect(d.activities).toBeTruthy();
      expect(Array.isArray(d.reviews)).toBe(true);
      expect(Array.isArray(d.state_logs)).toBe(true);
    });
  });
});

describe("buildSeedDashboard — non-empty dashboard", () => {
  it("returns projects and progress lists derived from the fixtures", () => {
    const dashboard = buildSeedDashboard();
    expect(dashboard.projects.length).toBeGreaterThan(0);
    expect(dashboard.progress.length).toBeGreaterThan(0);

    const projectIds = new Set(dashboard.projects.map((p) => p.id));
    dashboard.progress.forEach((a) => {
      expect(projectIds.has(a.project)).toBe(true);
    });
  });
});

describe("seedAdapter — single entry point", () => {
  it("exposes the full seeded state for the dev flow", () => {
    const seed = seedAdapter();
    expect(seed.projects.length).toBeGreaterThan(0);
    expect(seed.advances.length).toBeGreaterThan(0);
    expect(seed.dashboard.projects.length).toBeGreaterThan(0);
    expect(seed.dashboard.progress.length).toBeGreaterThan(0);
    expect(seed.advanceDetails).toBe(fixtureAdvanceDetails);
  });
});