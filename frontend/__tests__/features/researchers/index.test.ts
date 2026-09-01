/**
 * Researchers feature barrel — public API surface.
 *
 * Design (researchers): the feature index re-exports the contracts,
 * schemas, lifecycle config, authorization helpers, hooks and components.
 * This test exercises the barrel so re-export statements are covered and
 * the public surface stays stable.
 */

import {
  DOCUMENT_TYPES,
  researcherCreateSchema,
  researcherEditSchema,
  RESEARCHER_ACTIONS,
  getResearcherActions,
  isResearcherDeactivate,
  isAdminPlus,
  canDeactivateResearcher,
  canEditResearcher,
  useResearchersList,
  useResearcherDetail,
  useCreateResearcher,
  useUpdateResearcher,
  useDeactivateResearcher,
  CompletenessBar,
  getCompletenessState,
  ResearcherForm,
  ResearcherList,
  ResearcherDetail,
  DeactivateResearcherButton,
} from "@/features/researchers";

describe("researchers feature barrel", () => {
  it("re-exports the schemas and document types", () => {
    expect(DOCUMENT_TYPES).toContain("CC");
    expect(researcherCreateSchema).toBeDefined();
    expect(researcherEditSchema).toBeDefined();
  });

  it("re-exports the lifecycle and authorization helpers", () => {
    expect(RESEARCHER_ACTIONS[0]?.name).toBe("deactivate");
    expect(typeof getResearcherActions).toBe("function");
    expect(isResearcherDeactivate("deactivate")).toBe(true);
    expect(typeof isAdminPlus).toBe("function");
    expect(typeof canDeactivateResearcher).toBe("function");
    expect(typeof canEditResearcher).toBe("function");
  });

  it("re-exports the query/mutation hooks and components", () => {
    expect(typeof useResearchersList).toBe("function");
    expect(typeof useResearcherDetail).toBe("function");
    expect(typeof useCreateResearcher).toBe("function");
    expect(typeof useUpdateResearcher).toBe("function");
    expect(typeof useDeactivateResearcher).toBe("function");
    expect(typeof CompletenessBar).toBe("function");
    expect(typeof getCompletenessState).toBe("function");
    expect(typeof ResearcherForm).toBe("function");
    expect(typeof ResearcherList).toBe("function");
    expect(typeof ResearcherDetail).toBe("function");
    expect(typeof DeactivateResearcherButton).toBe("function");
  });
});
