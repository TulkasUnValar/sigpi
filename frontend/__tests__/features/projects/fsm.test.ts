/**
 * FSM action visibility — role + state filtered transitions.
 *
 * Spec (projects-ui FSM action bar):
 *   - Director actions show for a director on the matching source state.
 *   - Owner (PI) actions (submit/resubmit/finalize) show for a researcher.
 *   - Only destructive transitions (reject/cancel/close) require confirmation.
 *   - Terminal states expose no transitions.
 */

import {
  getProjectActions,
  isDestructiveAction,
  type ProjectAction,
} from "@/features/projects/fsm";

describe("getProjectActions — en_revision (director)", () => {
  it("shows approve/observe/return_to_draft/reject for a director", () => {
    const actions = getProjectActions("en_revision", ["director"]);
    const names = actions.map((a) => a.name);
    expect(names).toContain("approve");
    expect(names).toContain("observe");
    expect(names).toContain("return_to_draft");
    expect(names).toContain("reject");
  });

  it("does not show owner-only actions (submit/finalize) to a director", () => {
    const names = getProjectActions("en_revision", ["director"]).map(
      (a) => a.name,
    );
    expect(names).not.toContain("submit");
    expect(names).not.toContain("finalize");
  });

  it("hides all actions for a researcher on a director-gated state", () => {
    const actions = getProjectActions("en_revision", ["researcher"]);
    expect(actions).toHaveLength(0);
  });
});

describe("getProjectActions — owner-gated states", () => {
  it("shows submit for the owner on borrador", () => {
    const names = getProjectActions("borrador", ["researcher"]).map(
      (a) => a.name,
    );
    expect(names).toContain("submit");
  });

  it("shows resubmit for the owner on observado", () => {
    const names = getProjectActions("observado", ["researcher"]).map(
      (a) => a.name,
    );
    expect(names).toContain("resubmit");
  });

  it("hides owner actions on borrador for a director", () => {
    const actions = getProjectActions("borrador", ["director"]);
    expect(actions).toHaveLength(0);
  });
});

describe("getProjectActions — terminal states", () => {
  it("exposes no transitions when the project is cerrado", () => {
    expect(getProjectActions("cerrado", ["director"])).toHaveLength(0);
  });

  it("exposes no transitions when the project is rechazado", () => {
    expect(getProjectActions("rechazado", ["director"])).toHaveLength(0);
  });

  it("exposes no transitions when the project is cancelado", () => {
    expect(getProjectActions("cancelado", ["admin"])).toHaveLength(0);
  });
});

describe("getProjectActions — cancel requires admin", () => {
  it("shows cancel only to an admin on an active state", () => {
    const names = getProjectActions("en_ejecucion", ["admin"]).map(
      (a) => a.name,
    );
    expect(names).toContain("cancel");
  });

  it("hides cancel from a director", () => {
    const names = getProjectActions("en_ejecucion", ["director"]).map(
      (a) => a.name,
    );
    expect(names).not.toContain("cancel");
  });
});

describe("isDestructiveAction", () => {
  it("flags reject, cancel, and close as destructive", () => {
    expect(isDestructiveAction("reject")).toBe(true);
    expect(isDestructiveAction("cancel")).toBe(true);
    expect(isDestructiveAction("close")).toBe(true);
  });

  it("does not flag approve/observe/submit as destructive", () => {
    expect(isDestructiveAction("approve")).toBe(false);
    expect(isDestructiveAction("observe")).toBe(false);
    expect(isDestructiveAction("submit")).toBe(false);
  });
});

describe("getProjectActions — action labels are Spanish", () => {
  it("provides a Spanish label for every returned action", () => {
    const allActions = new Map<string, ProjectAction>();
    ["director", "researcher", "admin"].forEach((role) => {
      [
        "borrador",
        "enviado",
        "en_revision",
        "observado",
        "aprobado",
        "en_ejecucion",
        "suspendido",
        "finalizado",
        "en_cierre",
        "cerrado",
        "rechazado",
        "cancelado",
      ].forEach((state) => {
        getProjectActions(state, [role]).forEach((a) => allActions.set(a.name, a));
      });
    });

    expect(allActions.size).toBeGreaterThanOrEqual(10);
    allActions.forEach((a) => {
      expect(a.label.length).toBeGreaterThan(0);
    });
  });
});
