/**
 * Researchers fixtures — seed dataset integrity.
 *
 * Spec (researchers-ui): MSW fixtures produce paginated ResearcherList
 * rows and full details (with nested affiliations/profiles/attachments)
 * so /researchers renders real data without a backend.
 *
 * Note: the MSW handler behavior is exercised at runtime by the dev flow
 * (mocks/browser.ts + MswProvider) and by the component tests that mock
 * the api layer; the installed msw build cannot be loaded through
 * jest-resolve in this setup (raw .ts sources with #core imports).
 */

import {
  fixtureResearchers,
  fixtureResearcherDetails,
  fixtureAffiliations,
  fixtureExternalProfiles,
  fixtureAttachments,
} from "@/fixtures/researchers";

describe("researchers fixtures", () => {
  it("provides non-empty list rows with the required fields", () => {
    expect(fixtureResearchers.length).toBeGreaterThan(0);
    fixtureResearchers.forEach((r) => {
      expect(r.id).toBeTruthy();
      expect(r.full_name).toBeTruthy();
      expect(typeof r.is_active).toBe("boolean");
      expect(r.completeness_score).toBeGreaterThanOrEqual(0);
      expect(r.completeness_score).toBeLessThanOrEqual(100);
    });
  });

  it("provides full details for every list row", () => {
    fixtureResearchers.forEach((r) => {
      const detail = fixtureResearcherDetails[r.id];
      expect(detail).toBeTruthy();
      if (!detail) return;
      expect(detail.full_name).toBe(r.full_name);
      expect(Array.isArray(detail.affiliations)).toBe(true);
      expect(Array.isArray(detail.external_profiles)).toBe(true);
      expect(Array.isArray(detail.attachments)).toBe(true);
    });
  });

  it("includes an inactive researcher and a partial completeness score", () => {
    expect(fixtureResearchers.some((r) => !r.is_active)).toBe(true);
    expect(fixtureResearchers.some((r) => r.completeness_score < 100)).toBe(true);
  });

  it("references only the seeded institution", () => {
    fixtureResearchers.forEach((r) => {
      expect(r.institution).toBe("inst-1");
    });
  });

  it("provides nested affiliation/profile/attachment fixtures for a seeded researcher", () => {
    expect(fixtureAffiliations.length).toBeGreaterThan(0);
    expect(fixtureExternalProfiles.length).toBeGreaterThan(0);
    expect(fixtureAttachments.length).toBeGreaterThan(0);

    const r1Id = fixtureResearchers[0]!.id;
    expect(fixtureAffiliations.every((a) => a.researcher === r1Id)).toBe(true);
    expect(fixtureExternalProfiles.every((p) => p.researcher === r1Id)).toBe(true);
    expect(fixtureAttachments.every((a) => a.researcher === r1Id)).toBe(true);

    // The first affiliation is primary.
    expect(fixtureAffiliations.some((a) => a.is_primary)).toBe(true);

    // Attachments are metadata only — they carry an external_url, not a file.
    expect(fixtureAttachments.every((a) => a.external_url.length > 0)).toBe(true);
  });
});
