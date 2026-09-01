/**
 * Calls permissions + FSM action visibility — role and state filtered.
 *
 * Spec (calls-ui):
 *   - canManageCall: director+, director_centro alias, admin, superadmin.
 *   - getCallActions(state, roles): the 5 transitions filtered by source
 *     state and allowed role; archivada is terminal (no outbound actions).
 *   - archive is the only destructive transition (ConfirmDialog).
 */

import { canManageCall, MANAGER_ROLES } from "@/features/calls/permissions";
import { getCallActions, isDestructiveCallAction, type CallAction } from "@/features/calls/fsm";

describe("canManageCall", () => {
  it("allows director, director_centro, admin and superadmin", () => {
    expect(canManageCall(["director"])).toBe(true);
    expect(canManageCall(["director_centro"])).toBe(true);
    expect(canManageCall(["admin"])).toBe(true);
    expect(canManageCall(["superadmin"])).toBe(true);
  });

  it("denies researcher and empty roles", () => {
    expect(canManageCall(["researcher"])).toBe(false);
    expect(canManageCall([])).toBe(false);
  });

  it("allows when any role is a manager (mixed roles)", () => {
    expect(canManageCall(["researcher", "director"])).toBe(true);
  });

  it("exposes the manager role list for RoleGuard gating", () => {
    expect(MANAGER_ROLES).toContain("director");
    expect(MANAGER_ROLES).toContain("director_centro");
    expect(MANAGER_ROLES).toContain("admin");
    expect(MANAGER_ROLES).toContain("superadmin");
  });
});

describe("getCallActions — linear lifecycle (director)", () => {
  it("shows open_call on borrador", () => {
    const names = getCallActions("borrador", ["director"]).map((a) => a.name);
    expect(names).toContain("open_call");
    expect(names).not.toContain("close_call");
  });

  it("shows close_call on abierta", () => {
    const names = getCallActions("abierta", ["director"]).map((a) => a.name);
    expect(names).toContain("close_call");
  });

  it("shows start_evaluation on cerrada", () => {
    const names = getCallActions("cerrada", ["director"]).map((a) => a.name);
    expect(names).toContain("start_evaluation");
  });

  it("shows publish_results on en_evaluacion", () => {
    const names = getCallActions("en_evaluacion", ["director"]).map((a) => a.name);
    expect(names).toContain("publish_results");
  });
});

describe("getCallActions — archive sources and terminal state", () => {
  it("offers archive from cerrada and resultados_publicados", () => {
    expect(getCallActions("cerrada", ["director"]).map((a) => a.name)).toContain("archive");
    expect(getCallActions("resultados_publicados", ["director"]).map((a) => a.name)).toContain(
      "archive",
    );
  });

  it("hides archive from abierta and en_evaluacion", () => {
    expect(getCallActions("abierta", ["director"]).map((a) => a.name)).not.toContain("archive");
    expect(getCallActions("en_evaluacion", ["director"]).map((a) => a.name)).not.toContain(
      "archive",
    );
  });

  it("exposes no actions when the call is archivada (terminal)", () => {
    expect(getCallActions("archivada", ["director"])).toHaveLength(0);
    expect(getCallActions("archivada", ["superadmin"])).toHaveLength(0);
  });
});

describe("getCallActions — role filtering", () => {
  it("shows no actions to a researcher on cerrada", () => {
    expect(getCallActions("cerrada", ["researcher"])).toHaveLength(0);
  });

  it("shows no actions to a researcher on borrador", () => {
    expect(getCallActions("borrador", ["researcher"])).toHaveLength(0);
  });

  it("respects the director_centro alias role", () => {
    const names = getCallActions("borrador", ["director_centro"]).map((a) => a.name);
    expect(names).toContain("open_call");
  });
});

describe("isDestructiveCallAction", () => {
  it("flags archive as destructive", () => {
    expect(isDestructiveCallAction("archive")).toBe(true);
  });

  it("does not flag the other four transitions as destructive", () => {
    expect(isDestructiveCallAction("open_call")).toBe(false);
    expect(isDestructiveCallAction("close_call")).toBe(false);
    expect(isDestructiveCallAction("start_evaluation")).toBe(false);
    expect(isDestructiveCallAction("publish_results")).toBe(false);
  });
});

describe("getCallActions — Spanish labels", () => {
  it("provides a non-empty Spanish label for every action", () => {
    const allActions = new Map<string, CallAction>();
    MANAGER_ROLES.forEach((role) => {
      [
        "borrador",
        "abierta",
        "cerrada",
        "en_evaluacion",
        "resultados_publicados",
        "archivada",
      ].forEach((state) => {
        getCallActions(state, [role]).forEach((a) => allActions.set(a.name, a));
      });
    });

    expect(allActions.size).toBe(5);
    allActions.forEach((a) => {
      expect(a.label.length).toBeGreaterThan(0);
    });
  });
});
