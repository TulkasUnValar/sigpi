/**
 * Tests for the institutions query-key factory (lib/query-keys.ts).
 *
 * Design (institutions): queryKeys.institutions mirrors the projects
 * factory with an (scope, kind, parentId) list signature. Root list and
 * detail use scope = null (institution-agnostic).
 */

import { queryKeys } from "@/lib/query-keys";

describe("queryKeys.institutions", () => {
  it("anchors all institution keys under ['institutions']", () => {
    expect(queryKeys.institutions.all).toEqual(["institutions"]);
  });

  it("builds a root list key with null scope and institution kind", () => {
    expect(queryKeys.institutions.list(null, "institution", null)).toEqual([
      "institutions",
      "list",
      null,
      "institution",
      null,
    ]);
  });

  it("builds child list keys scoped by institution and parent id", () => {
    expect(queryKeys.institutions.list("inst-1", "sede", "sede-9")).toEqual([
      "institutions",
      "list",
      "inst-1",
      "sede",
      "sede-9",
    ]);
  });

  it("builds detail keys with scope, kind and entity id", () => {
    expect(queryKeys.institutions.detail(null, "institution", "inst-1")).toEqual([
      "institutions",
      "detail",
      null,
      "institution",
      "inst-1",
    ]);
  });

  it("builds nested detail keys with an active scope", () => {
    expect(queryKeys.institutions.detail("inst-1", "center", "center-2")).toEqual([
      "institutions",
      "detail",
      "inst-1",
      "center",
      "center-2",
    ]);
  });
});
