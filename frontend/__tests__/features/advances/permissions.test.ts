/**
 * Advance permission helpers — RF-043/044.
 */

import { canEditAdvance, canDeleteAdvance } from "@/features/advances/permissions";
import type { AdvanceDetail } from "@/features/advances/types";

function makeAdvance(status: string, createdBy: string): AdvanceDetail {
  return {
    id: "a1",
    institution: "inst-1",
    project: "p1",
    created_by: createdBy,
    period_start: "2026-01-01",
    period_end: "2026-03-31",
    description: "Desc",
    cumulative_percentage: 25,
    activities: "Act",
    difficulties: "",
    next_steps: "",
    status,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    documents: [],
    reviews: [],
    state_logs: [],
  };
}

describe("canEditAdvance", () => {
  it("returns true for borrador", () => {
    expect(canEditAdvance(makeAdvance("borrador", "u1"))).toBe(true);
  });

  it("returns false for non-borrador states", () => {
    expect(canEditAdvance(makeAdvance("enviado", "u1"))).toBe(false);
    expect(canEditAdvance(makeAdvance("en_revision", "u1"))).toBe(false);
    expect(canEditAdvance(makeAdvance("aprobado", "u1"))).toBe(false);
    expect(canEditAdvance(makeAdvance("observado", "u1"))).toBe(false);
    expect(canEditAdvance(makeAdvance("rechazado", "u1"))).toBe(false);
  });
});

describe("canDeleteAdvance", () => {
  it("returns true for borrador when user is creator", () => {
    expect(canDeleteAdvance(makeAdvance("borrador", "u1"), "u1")).toBe(true);
  });

  it("returns false for borrador when user is not creator", () => {
    expect(canDeleteAdvance(makeAdvance("borrador", "u1"), "u2")).toBe(false);
  });

  it("returns false for non-borrador even when user is creator", () => {
    expect(canDeleteAdvance(makeAdvance("enviado", "u1"), "u1")).toBe(false);
    expect(canDeleteAdvance(makeAdvance("aprobado", "u1"), "u1")).toBe(false);
  });

  it("returns false when userId is null", () => {
    expect(canDeleteAdvance(makeAdvance("borrador", "u1"), null)).toBe(false);
  });
});
