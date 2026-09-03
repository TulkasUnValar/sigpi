/**
 * Reports query-key factory — institution-scoped keys.
 *
 * Spec (frontend-reports 1.5): the reports factory provides `all`,
 * `preview(institutionId, type, id)`, `pdf(...)` and the derived-view key,
 * all scoped by the active institution like the other factories.
 */

import { queryKeys } from "@/lib/query-keys";

describe("queryKeys.reports", () => {
  it("anchors all reports keys under ['reports']", () => {
    expect(queryKeys.reports.all).toEqual(["reports"]);
  });

  it("scopes preview keys by institution, type and entity id", () => {
    expect(queryKeys.reports.preview("inst-1", "project", "p1")).toEqual([
      "reports",
      "preview",
      "inst-1",
      "project",
      "p1",
    ]);
    expect(queryKeys.reports.preview("inst-1", "advances", "p3")).toEqual([
      "reports",
      "preview",
      "inst-1",
      "advances",
      "p3",
    ]);
  });

  it("supports a null institution when no scope is active", () => {
    expect(queryKeys.reports.preview(null, "center", "c1")).toEqual([
      "reports",
      "preview",
      null,
      "center",
      "c1",
    ]);
  });

  it("scopes pdf keys by institution, type and id", () => {
    expect(queryKeys.reports.pdf("inst-1", "researcher", "r1")).toEqual([
      "reports",
      "pdf",
      "inst-1",
      "researcher",
      "r1",
    ]);
  });

  it("scopes the derived view key by institution, type and id", () => {
    expect(queryKeys.reports.derived("inst-1", "project", "p1")).toEqual([
      "reports",
      "derived",
      "inst-1",
      "project",
      "p1",
    ]);
  });
});
