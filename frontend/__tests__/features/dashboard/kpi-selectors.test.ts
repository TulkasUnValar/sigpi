/**
 * Tests for dashboard KPI selectors — role-aware composition from
 * /projects/ and /progress/ list endpoints.
 *
 * Spec (dashboard):
 *   Director queue: pending-approvals queue + KPI cards.
 *   Investigator KPIs: "my projects" and progress KPIs; approvals hidden.
 */

import {
  computeDirectorKpis,
  computeInvestigatorKpis,
  selectPendingApprovals,
  type ProjectSummary,
  type ProgressSummary,
} from "@/features/dashboard/kpi-selectors";

const projects: ProjectSummary[] = [
  { id: "p1", title: "Alpha", status: "en_revision" },
  { id: "p2", title: "Beta", status: "en_revision" },
  { id: "p3", title: "Gamma", status: "aprobado" },
  { id: "p4", title: "Delta", status: "en_ejecucion" },
];

const progress: ProgressSummary[] = [
  { id: "a1", project: "p1", status: "en_revision", cumulative_percentage: 30 },
  { id: "a2", project: "p1", status: "aprobado", cumulative_percentage: 45 },
  { id: "a3", project: "p4", status: "en_revision", cumulative_percentage: 60 },
];

describe("selectPendingApprovals", () => {
  it("returns projects awaiting director review (en_revision)", () => {
    const pending = selectPendingApprovals(projects);
    expect(pending).toHaveLength(2);
    expect(pending.map((p) => p.id)).toEqual(["p1", "p2"]);
  });

  it("returns empty when no project is in review", () => {
    const noReview = projects.filter((p) => p.status !== "en_revision");
    const pending = selectPendingApprovals(noReview);
    expect(pending).toHaveLength(0);
  });
});

describe("computeDirectorKpis", () => {
  it("counts pending projects and total active projects", () => {
    const kpis = computeDirectorKpis(projects, progress);
    expect(kpis.totalProjects).toBe(4);
    expect(kpis.pendingApprovals).toBe(2);
    expect(kpis.pendingAdvances).toBe(2); // advances in en_revision
  });
});

describe("computeInvestigatorKpis", () => {
  it("counts my projects (approved/executing) and average progress", () => {
    const kpis = computeInvestigatorKpis(projects, progress);
    // "my projects": aprobado + en_ejecucion
    expect(kpis.myProjects).toBe(2);
    // average cumulative_percentage across advances
    expect(kpis.averageProgress).toBe(45);
  });

  it("returns zero progress when there are no advances", () => {
    const kpis = computeInvestigatorKpis(projects, []);
    expect(kpis.averageProgress).toBe(0);
  });
});