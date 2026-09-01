/**
 * Researchers FSM — lifecycle state transitions.
 *
 * Spec (researchers-ui deactivate): only a single `deactivate` transition
 * is modeled (no activate/archive/me endpoints exist on the backend).
 * Deactivate is admin+ (level ≤ 2) and only from the active state.
 */

import {
  getResearcherActions,
  isResearcherDeactivate,
  RESEARCHER_ACTIONS,
} from "@/features/researchers/fsm";

describe("RESEARCHER_ACTIONS", () => {
  it("models exactly one lifecycle action (deactivate)", () => {
    expect(RESEARCHER_ACTIONS).toHaveLength(1);
    expect(RESEARCHER_ACTIONS[0]?.name).toBe("deactivate");
  });

  it("marks deactivate as destructive (ConfirmDialog)", () => {
    expect(isResearcherDeactivate("deactivate")).toBe(true);
    expect(isResearcherDeactivate("activate")).toBe(false);
  });
});

describe("getResearcherActions", () => {
  it("offers deactivate to an admin on an active researcher", () => {
    const actions = getResearcherActions("active", ["admin"]);
    expect(actions.map((a) => a.name)).toEqual(["deactivate"]);
  });

  it("offers deactivate to a superadmin on an active researcher", () => {
    const actions = getResearcherActions("active", ["superadmin"]);
    expect(actions.map((a) => a.name)).toEqual(["deactivate"]);
  });

  it("hides deactivate for non-admin roles", () => {
    expect(getResearcherActions("active", ["director"])).toHaveLength(0);
    expect(getResearcherActions("active", ["researcher"])).toHaveLength(0);
  });

  it("hides deactivate when the researcher is already inactive", () => {
    expect(getResearcherActions("inactive", ["admin"])).toHaveLength(0);
  });
});
