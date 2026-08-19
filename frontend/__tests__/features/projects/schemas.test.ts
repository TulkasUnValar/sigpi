/**
 * Project wizard step schemas — per-step validation.
 *
 * Spec (projects-ui create wizard):
 *   basic → center/group/line → team → documents, each with per-step
 *   validation and a review step before submit.
 */

import {
  basicStepSchema,
  classificationStepSchema,
  teamStepSchema,
} from "@/features/projects/schemas";

describe("basicStepSchema", () => {
  it("accepts a fully populated basic step", () => {
    const result = basicStepSchema.safeParse({
      title: "Estudio de biodiversidad",
      abstract: "Resumen del proyecto.",
      objectives: "Objetivos generales.",
      methodology: "Metodología propuesta.",
      expected_results: "Resultados esperados.",
      keywords: "biodiversidad, flora",
      start_date: "2026-01-10",
      estimated_end_date: "2027-01-10",
    });
    expect(result.success).toBe(true);
  });

  it("rejects a missing title and empty dates", () => {
    const result = basicStepSchema.safeParse({
      title: "",
      abstract: "Resumen.",
      objectives: "Objetivos.",
      methodology: "Método.",
      expected_results: "Resultados.",
      keywords: "",
      start_date: "",
      estimated_end_date: "2025-01-01",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      const issues = result.error.issues.map((i) => i.path[0]);
      expect(issues).toContain("title");
      expect(issues).toContain("start_date");
    }
  });

  it("rejects when estimated_end_date precedes start_date", () => {
    const result = basicStepSchema.safeParse({
      title: "Título",
      abstract: "Resumen.",
      objectives: "Objetivos.",
      methodology: "Método.",
      expected_results: "Resultados.",
      keywords: "",
      start_date: "2026-06-01",
      estimated_end_date: "2026-01-01",
    });
    expect(result.success).toBe(false);
  });
});

describe("classificationStepSchema", () => {
  it("accepts a center with optional group/line", () => {
    const result = classificationStepSchema.safeParse({
      center: "c1",
      group: "",
      line: "",
    });
    expect(result.success).toBe(true);
  });

  it("rejects a missing center", () => {
    const result = classificationStepSchema.safeParse({
      center: "",
      group: "",
      line: "",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.map((i) => i.path[0])).toContain("center");
    }
  });
});

describe("teamStepSchema", () => {
  it("accepts an empty team (members optional)", () => {
    const result = teamStepSchema.safeParse({ members: [] });
    expect(result.success).toBe(true);
  });

  it("rejects a member without a role", () => {
    const result = teamStepSchema.safeParse({
      members: [{ researcher: "r1", role: "" }],
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.map((i) => i.path.join("."))).toContain(
        "members.0.role",
      );
    }
  });
});
