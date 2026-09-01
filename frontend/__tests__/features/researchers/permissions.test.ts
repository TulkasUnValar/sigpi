/**
 * Researchers authorization helpers — edit and deactivate gates.
 *
 * Spec (researchers-ui): update is allowed for admin+ (level ≤ 2) or the
 * linked self (owning researcher); deactivate is admin+ only.
 */

import {
  canDeactivateResearcher,
  canEditResearcher,
  isAdminPlus,
} from "@/features/researchers/permissions";

describe("isAdminPlus", () => {
  it("returns true for admin and superadmin", () => {
    expect(isAdminPlus(["admin"])).toBe(true);
    expect(isAdminPlus(["superadmin"])).toBe(true);
  });

  it("returns false for director and researcher", () => {
    expect(isAdminPlus(["director"])).toBe(false);
    expect(isAdminPlus(["researcher"])).toBe(false);
  });
});

describe("canDeactivateResearcher", () => {
  it("allows admin and superadmin", () => {
    expect(canDeactivateResearcher(["admin"])).toBe(true);
    expect(canDeactivateResearcher(["superadmin"])).toBe(true);
  });

  it("denies director and researcher", () => {
    expect(canDeactivateResearcher(["director"])).toBe(false);
    expect(canDeactivateResearcher(["researcher"])).toBe(false);
  });
});

describe("canEditResearcher", () => {
  const detail = {
    user: "u-1",
    id: "r-1",
    institution: "inst-1",
    first_name: "Ana",
    last_name: "Pérez",
    document_type: "CC",
    document_number: "123",
    primary_email: "ana@example.com",
    phone: "",
    bio: "",
    academic_formation: "",
    is_active: true,
    full_name: "Ana Pérez",
    completeness_score: 40,
    affiliations: [],
    external_profiles: [],
    attachments: [],
    created_at: "",
    updated_at: "",
  };

  it("allows admin+ regardless of linked user", () => {
    expect(canEditResearcher(detail, null, ["admin"])).toBe(true);
    expect(canEditResearcher(detail, "other", ["superadmin"])).toBe(true);
  });

  it("allows the linked self to edit", () => {
    expect(canEditResearcher(detail, "u-1", ["researcher"])).toBe(true);
  });

  it("denies a non-linked director/researcher", () => {
    expect(canEditResearcher(detail, "u-2", ["director"])).toBe(false);
    expect(canEditResearcher(detail, "u-2", ["researcher"])).toBe(false);
  });

  it("denies when no user is linked and the role is not admin+", () => {
    expect(canEditResearcher({ ...detail, user: null }, "u-1", ["director"])).toBe(false);
  });
});
