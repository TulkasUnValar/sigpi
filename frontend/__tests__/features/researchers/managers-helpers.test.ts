/**
 * Nested managers — pure validation/formatting helpers.
 *
 * Spec (researchers-ui affiliations / profiles / attachments):
 *   - An affiliation needs at least one FK (center/group/line).
 *   - The first affiliation of a researcher is primary.
 *   - A profile needs a provider and a non-empty url.
 *   - An attachment needs a name, a type and an external_url.
 */

import {
  hasAffiliationSelection,
  isFirstAffiliation,
  affiliationLabel,
} from "@/features/researchers/AffiliationsManager";
import { profileFormValid } from "@/features/researchers/ExternalProfilesManager";
import { attachmentFormValid } from "@/features/researchers/AttachmentsManager";

describe("hasAffiliationSelection", () => {
  it("is true when at least one FK level is selected", () => {
    expect(hasAffiliationSelection("center-1", "", "")).toBe(true);
    expect(hasAffiliationSelection("", "group-1", "")).toBe(true);
    expect(hasAffiliationSelection("", "", "line-1")).toBe(true);
  });

  it("is false when no FK level is selected", () => {
    expect(hasAffiliationSelection("", "", "")).toBe(false);
  });
});

describe("isFirstAffiliation", () => {
  it("is true only for the first affiliation", () => {
    expect(isFirstAffiliation(0)).toBe(true);
    expect(isFirstAffiliation(1)).toBe(false);
    expect(isFirstAffiliation(5)).toBe(false);
  });
});

describe("affiliationLabel", () => {
  it("joins the non-empty FK ids with separators", () => {
    expect(
      affiliationLabel({
        id: "a1",
        center: "c1",
        group: "g1",
        line: "l1",
        is_primary: false,
        researcher: "r",
        created_at: "",
      }),
    ).toBe("c1 · g1 · l1");
  });

  it("falls back when no FK ids are present", () => {
    expect(
      affiliationLabel({
        id: "a1",
        center: null,
        group: null,
        line: null,
        is_primary: false,
        researcher: "r",
        created_at: "",
      }),
    ).toBe("Sin datos");
  });
});

describe("profileFormValid", () => {
  it("requires a provider and a non-empty url", () => {
    expect(profileFormValid("orcid", "https://orcid.org/1")).toBe(true);
    expect(profileFormValid("", "https://orcid.org/1")).toBe(false);
    expect(profileFormValid("orcid", "   ")).toBe(false);
  });
});

describe("attachmentFormValid", () => {
  it("requires name, type and external_url", () => {
    expect(attachmentFormValid("CV", "cv", "https://example.com/cv.pdf")).toBe(true);
    expect(attachmentFormValid("", "cv", "https://example.com/cv.pdf")).toBe(false);
    expect(attachmentFormValid("CV", "", "https://example.com/cv.pdf")).toBe(false);
    expect(attachmentFormValid("CV", "cv", "   ")).toBe(false);
  });
});
