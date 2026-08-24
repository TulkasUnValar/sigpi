/**
 * Advances FSM action visibility — role + state filtered transitions.
 *
 * Spec (advances-ui FSM):
 *   - Director actions (approve/observe/reject/return_to_draft) show for a
 *     director on the matching source state.
 *   - reject is destructive → ConfirmDialog (tested at the action-bar level).
 *   - Creator actions (submit/resubmit) show for a researcher member.
 *   - Terminal state (aprobado) exposes no outbound transitions.
 */

import {
  getAdvanceActions,
  isDestructiveAdvanceAction,
  type AdvanceAction,
} from "@/features/advances/fsm";

describe("getAdvanceActions — en_revision (director)", () => {
  it("shows approve/observe/return_to_draft/reject for a director", () => {
    const actions = getAdvanceActions("en_revision", ["director"]);
    const names = actions.map((a) => a.name);
    expect(names).toContain("approve");
    expect(names).toContain("observe");
    expect(names).toContain("return_to_draft");
    expect(names).toContain("reject");
  });

  it("does not show creator-only actions (submit/resubmit) to a director", () => {
    const names = getAdvanceActions("en_revision", ["director"]).map(
      (a) => a.name,
    );
    expect(names).not.toContain("submit");
    expect(names).not.toContain("resubmit");
  });

  it("hides all actions for a researcher on a director-gated state", () => {
    expect(getAdvanceActions("en_revision", ["researcher"])).toHaveLength(0);
  });
});

describe("getAdvanceActions — creator-gated states", () => {
  it("shows submit for the creator on borrador", () => {
    const names = getAdvanceActions("borrador", ["researcher"]).map(
      (a) => a.name,
    );
    expect(names).toContain("submit");
  });

  it("shows resubmit for the creator on observado", () => {
    const names = getAdvanceActions("observado", ["researcher"]).map(
      (a) => a.name,
    );
    expect(names).toContain("resubmit");
  });

  it("hides creator actions on borrador for a director", () => {
    expect(getAdvanceActions("borrador", ["director"])).toHaveLength(0);
  });
});

describe("getAdvanceActions — accept_review from enviado", () => {
  it("shows accept_review to a director on enviado", () => {
    const names = getAdvanceActions("enviado", ["director"]).map(
      (a) => a.name,
    );
    expect(names).toContain("accept_review");
  });

  it("hides accept_review from a researcher member", () => {
    const names = getAdvanceActions("enviado", ["researcher"]).map(
      (a) => a.name,
    );
    expect(names).not.toContain("accept_review");
  });
});

describe("getAdvanceActions — terminal state", () => {
  it("exposes no transitions when the advance is aprobado", () => {
    expect(getAdvanceActions("aprobado", ["director"])).toHaveLength(0);
    expect(getAdvanceActions("aprobado", ["researcher"])).toHaveLength(0);
  });
});

describe("isDestructiveAdvanceAction", () => {
  it("flags reject as destructive", () => {
    expect(isDestructiveAdvanceAction("reject")).toBe(true);
  });

  it("does not flag approve/observe/return_to_draft/submit as destructive", () => {
    expect(isDestructiveAdvanceAction("approve")).toBe(false);
    expect(isDestructiveAdvanceAction("observe")).toBe(false);
    expect(isDestructiveAdvanceAction("return_to_draft")).toBe(false);
    expect(isDestructiveAdvanceAction("submit")).toBe(false);
  });
});

describe("getAdvanceActions — Spanish labels", () => {
  it("provides a non-empty Spanish label for every returned action", () => {
    const allActions = new Map<string, AdvanceAction>();
    ["director", "researcher", "admin"].forEach((role) => {
      [
        "borrador",
        "enviado",
        "en_revision",
        "observado",
        "aprobado",
        "rechazado",
      ].forEach((state) => {
        getAdvanceActions(state, [role]).forEach((a) =>
          allActions.set(a.name, a),
        );
      });
    });

    expect(allActions.size).toBeGreaterThanOrEqual(5);
    allActions.forEach((a) => {
      expect(a.label.length).toBeGreaterThan(0);
    });
  });
});