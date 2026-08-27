/**
 * Institutions FSM — activate/deactivate/archive action visibility.
 *
 * Spec (institutions-ui RF-F04):
 *   - activate shows from deactivated; deactivate from active;
 *     archive from active|deactivated.
 *   - Destructive actions (deactivate, archive) require ConfirmDialog.
 *   - Archived is terminal — no transition actions appear.
 *   - Institution-level writes are superadmin-only (backend IsSuperAdmin).
 */

import {
  getEntityActions,
  isDestructiveEntityAction,
  type FsmAction,
} from "@/features/institutions/fsm";

describe("getEntityActions — active", () => {
  it("shows deactivate + archive for a superadmin on an active node", () => {
    const names = getEntityActions("active", ["superadmin"]).map((a) => a.name);
    expect(names).toContain("deactivate");
    expect(names).toContain("archive");
    expect(names).not.toContain("activate");
  });

  it("hides all actions for non-superadmin roles on an active node", () => {
    expect(getEntityActions("active", ["admin"])).toHaveLength(0);
    expect(getEntityActions("active", ["director"])).toHaveLength(0);
    expect(getEntityActions("active", ["researcher"])).toHaveLength(0);
  });
});

describe("getEntityActions — deactivated", () => {
  it("shows activate + archive for a superadmin on a deactivated node", () => {
    const names = getEntityActions("deactivated", ["superadmin"]).map((a) => a.name);
    expect(names).toContain("activate");
    expect(names).toContain("archive");
    expect(names).not.toContain("deactivate");
  });
});

describe("getEntityActions — archived is terminal", () => {
  it("exposes no transition actions for any role", () => {
    expect(getEntityActions("archived", ["superadmin"])).toHaveLength(0);
    expect(getEntityActions("archived", ["admin"])).toHaveLength(0);
    expect(getEntityActions("archived", ["director"])).toHaveLength(0);
  });
});

describe("isDestructiveEntityAction", () => {
  it("flags deactivate and archive as destructive", () => {
    expect(isDestructiveEntityAction("deactivate")).toBe(true);
    expect(isDestructiveEntityAction("archive")).toBe(true);
  });

  it("does not flag activate as destructive", () => {
    expect(isDestructiveEntityAction("activate")).toBe(false);
  });
});

describe("getEntityActions — config completeness", () => {
  it("provides Spanish labels and non-empty fromStates/allowedRoles", () => {
    const seen = new Map<string, FsmAction>();
    ["superadmin", "admin", "director", "researcher"].forEach((role) => {
      ["active", "deactivated", "archived"].forEach((state) => {
        getEntityActions(state, [role]).forEach((a) => seen.set(a.name, a));
      });
    });

    expect(seen.size).toBeGreaterThanOrEqual(3);
    seen.forEach((a) => {
      expect(a.label.length).toBeGreaterThan(0);
      expect(a.fromStates.length).toBeGreaterThan(0);
      expect(a.allowedRoles.length).toBeGreaterThan(0);
    });
  });

  it("archive is available from both active and deactivated", () => {
    const archive = getEntityActions("active", ["superadmin"]).find((a) => a.name === "archive");
    expect(archive).toBeDefined();
    expect(archive?.fromStates).toEqual(expect.arrayContaining(["active", "deactivated"]));
  });
});

describe("getEntityActions — write-role threshold (RF-F05)", () => {
  it("admins see child-entity actions when minRoles includes admin", () => {
    const names = getEntityActions("active", ["admin"], ["admin", "superadmin"]).map((a) => a.name);
    expect(names).toContain("deactivate");
    expect(names).toContain("archive");
  });

  it("directors are still denied when minRoles requires admin", () => {
    const names = getEntityActions("active", ["director"], ["admin", "superadmin"]).map(
      (a) => a.name,
    );
    expect(names).not.toContain("deactivate");
    expect(names).not.toContain("archive");
  });

  it("a superadmin passes a minRoles threshold that excludes superadmin", () => {
    expect(getEntityActions("active", ["superadmin"], ["admin"])).toHaveLength(0);
  });

  it("omitting minRoles keeps the superadmin-only default (institutions)", () => {
    expect(getEntityActions("active", ["admin"])).toHaveLength(0);
    expect(getEntityActions("active", ["superadmin"]).length).toBeGreaterThan(0);
  });
});
