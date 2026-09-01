/**
 * Tests for the researchers query-key factory (lib/query-keys.ts).
 *
 * Design (researchers): queryKeys.researchers is institution-scoped with
 * list/detail/nested key signatures so a mutation can invalidate the
 * whole researcher tree via `queryKeys.researchers.all`.
 */

import { queryKeys } from "@/lib/query-keys";

describe("queryKeys.researchers", () => {
  it("anchors all researcher keys under ['researchers']", () => {
    expect(queryKeys.researchers.all).toEqual(["researchers"]);
  });

  it("builds a paginated list key scoped by institution and page", () => {
    expect(queryKeys.researchers.list("inst-1", 1)).toEqual(["researchers", "list", "inst-1", 1]);
    expect(queryKeys.researchers.list("inst-1", 2)).toEqual(["researchers", "list", "inst-1", 2]);
  });

  it("builds a detail key scoped by institution and id", () => {
    expect(queryKeys.researchers.detail("inst-1", "r-1")).toEqual([
      "researchers",
      "detail",
      "inst-1",
      "r-1",
    ]);
  });

  it("builds nested list keys for affiliations/profiles/attachments", () => {
    expect(queryKeys.researchers.affiliations("inst-1", "r-1")).toEqual([
      "researchers",
      "detail",
      "inst-1",
      "r-1",
      "affiliations",
    ]);
    expect(queryKeys.researchers.profiles("inst-1", "r-1")).toEqual([
      "researchers",
      "detail",
      "inst-1",
      "r-1",
      "profiles",
    ]);
    expect(queryKeys.researchers.attachments("inst-1", "r-1")).toEqual([
      "researchers",
      "detail",
      "inst-1",
      "r-1",
      "attachments",
    ]);
  });
});
