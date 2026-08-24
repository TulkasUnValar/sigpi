/**
 * Advance create schema — zod validation for the create form.
 *
 * Spec (advances-ui create):
 *   Create form fields: period, %, activities, difficulties, next steps.
 *   RN-P01: 0 <= cumulative_percentage <= 100.
 *   RN-P02: period_end >= period_start.
 */

import { advanceCreateSchema } from "@/features/advances/schemas";

const validDraft = {
  period_start: "2026-01-01",
  period_end: "2026-03-31",
  cumulative_percentage: "25",
  description: "Avance del primer trimestre.",
  activities: "Recolección de datos; análisis preliminar.",
  difficulties: "",
  next_steps: "",
};

describe("advanceCreateSchema — valid input", () => {
  it("accepts a complete valid advance draft", () => {
    const result = advanceCreateSchema.safeParse(validDraft);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.cumulative_percentage).toBe(25);
    }
  });

  it("coerces the percentage string into a number", () => {
    const result = advanceCreateSchema.safeParse(validDraft);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(typeof result.data.cumulative_percentage).toBe("number");
      expect(result.data.cumulative_percentage).toBe(25);
    }
  });

  it("defaults optional fields (difficulties, next_steps) to empty strings", () => {
    const result = advanceCreateSchema.safeParse(validDraft);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.difficulties).toBe("");
      expect(result.data.next_steps).toBe("");
    }
  });
});

describe("advanceCreateSchema — required fields", () => {
  it.each([
    ["period_start", { period_start: "" }],
    ["period_end", { period_end: "" }],
    ["description", { description: "" }],
    ["activities", { activities: "" }],
  ])("rejects an empty %s", (field, overrides) => {
    const result = advanceCreateSchema.safeParse({ ...validDraft, ...overrides });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path[0] === field)).toBe(true);
    }
  });

  it("rejects a missing cumulative_percentage", () => {
    const result = advanceCreateSchema.safeParse({
      ...validDraft,
      cumulative_percentage: "",
    });
    expect(result.success).toBe(false);
  });
});

describe("advanceCreateSchema — percentage range (RN-P01)", () => {
  it("rejects a percentage below 0", () => {
    const result = advanceCreateSchema.safeParse({
      ...validDraft,
      cumulative_percentage: "-5",
    });
    expect(result.success).toBe(false);
  });

  it("rejects a percentage above 100", () => {
    const result = advanceCreateSchema.safeParse({
      ...validDraft,
      cumulative_percentage: "120",
    });
    expect(result.success).toBe(false);
  });

  it("accepts the boundaries 0 and 100", () => {
    expect(
      advanceCreateSchema.safeParse({
        ...validDraft,
        cumulative_percentage: "0",
      }).success,
    ).toBe(true);
    expect(
      advanceCreateSchema.safeParse({
        ...validDraft,
        cumulative_percentage: "100",
      }).success,
    ).toBe(true);
  });
});

describe("advanceCreateSchema — period dates (RN-P02)", () => {
  it("rejects period_end before period_start", () => {
    const result = advanceCreateSchema.safeParse({
      ...validDraft,
      period_start: "2026-06-01",
      period_end: "2026-01-01",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.some((i) => i.path[0] === "period_end")).toBe(
        true,
      );
    }
  });

  it("accepts period_end equal to period_start", () => {
    const result = advanceCreateSchema.safeParse({
      ...validDraft,
      period_start: "2026-01-01",
      period_end: "2026-01-01",
    });
    expect(result.success).toBe(true);
  });
});