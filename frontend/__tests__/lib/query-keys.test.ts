/**
 * Tests for lib/query-keys.ts — TanStack Query key factories.
 *
 * Design (server-state): centralized key factories for `projects`,
 * `advances`, and `dashboard`, scoped by active institution so switching
 * institution can invalidate all scoped queries.
 */

import { queryKeys } from "@/lib/query-keys";

describe("queryKeys.projects", () => {
  it("anchors all projects keys under ['projects']", () => {
    expect(queryKeys.projects.all).toEqual(["projects"]);
  });

  it("scopes list keys by institution and filters", () => {
    expect(queryKeys.projects.list("inst-1", { status: "en_revision" })).toEqual([
      "projects",
      "list",
      "inst-1",
      { status: "en_revision" },
    ]);
  });

  it("supports null institution for institution-agnostic lists", () => {
    expect(queryKeys.projects.list(null)).toEqual(["projects", "list", null, {}]);
  });

  it("scopes detail keys by institution and project id", () => {
    expect(queryKeys.projects.detail("inst-1", "proj-9")).toEqual([
      "projects",
      "detail",
      "inst-1",
      "proj-9",
    ]);
  });
});

describe("queryKeys.advances", () => {
  it("anchors all advances keys under ['advances']", () => {
    expect(queryKeys.advances.all).toEqual(["advances"]);
  });

  it("scopes list keys by institution and optional project", () => {
    expect(queryKeys.advances.list("inst-1", "proj-9")).toEqual([
      "advances",
      "list",
      "inst-1",
      "proj-9",
    ]);
  });

  it("uses 'all' placeholder when no project filter applies", () => {
    expect(queryKeys.advances.list("inst-1")).toEqual([
      "advances",
      "list",
      "inst-1",
      "all",
    ]);
  });

  it("scopes detail keys by institution and advance id", () => {
    expect(queryKeys.advances.detail("inst-1", "adv-3")).toEqual([
      "advances",
      "detail",
      "inst-1",
      "adv-3",
    ]);
  });
});

describe("queryKeys.dashboard", () => {
  it("anchors dashboard keys under ['dashboard']", () => {
    expect(queryKeys.dashboard.all).toEqual(["dashboard"]);
  });

  it("scopes the projects KPI key by institution", () => {
    expect(queryKeys.dashboard.projects("inst-1")).toEqual([
      "dashboard",
      "projects",
      "inst-1",
    ]);
  });

  it("scopes the progress KPI key by institution", () => {
    expect(queryKeys.dashboard.progress("inst-1")).toEqual([
      "dashboard",
      "progress",
      "inst-1",
    ]);
  });
});