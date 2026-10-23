/**
 * Budgets schemas tests — zod validation for forms.
 *
 * Tests decimal validation, required fields, and payload builders.
 */

import {
  budgetFormSchema,
  budgetLineFormSchema,
  fundingSourceFormSchema,
  budgetExecutionFormSchema,
  budgetAttachmentFormSchema,
  buildCreateBudgetPayload,
  buildCreateBudgetLinePayload,
} from "@/features/budgets/schemas";

describe("budgetFormSchema", () => {
  it("validates a valid budget form", () => {
    const result = budgetFormSchema.safeParse({
      project: "project-1",
      name: "Presupuesto 2026",
      approved_amount: "10000.00",
    });
    expect(result.success).toBe(true);
  });

  it("rejects empty project", () => {
    const result = budgetFormSchema.safeParse({
      project: "",
      name: "Presupuesto 2026",
      approved_amount: "10000.00",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0].path).toContain("project");
    }
  });

  it("rejects empty name", () => {
    const result = budgetFormSchema.safeParse({
      project: "project-1",
      name: "",
      approved_amount: "10000.00",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0].path).toContain("name");
    }
  });

  it("rejects invalid decimal amount", () => {
    const result = budgetFormSchema.safeParse({
      project: "project-1",
      name: "Presupuesto 2026",
      approved_amount: "not-a-number",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0].path).toContain("approved_amount");
    }
  });

  it("rejects negative amount", () => {
    const result = budgetFormSchema.safeParse({
      project: "project-1",
      name: "Presupuesto 2026",
      approved_amount: "-100.00",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0].path).toContain("approved_amount");
    }
  });

  it("accepts zero amount", () => {
    const result = budgetFormSchema.safeParse({
      project: "project-1",
      name: "Presupuesto 2026",
      approved_amount: "0.00",
    });
    expect(result.success).toBe(true);
  });
});

describe("budgetLineFormSchema", () => {
  it("validates a valid line form", () => {
    const result = budgetLineFormSchema.safeParse({
      name: "Personal",
      approved_amount: "5000.00",
    });
    expect(result.success).toBe(true);
  });

  it("rejects empty name", () => {
    const result = budgetLineFormSchema.safeParse({
      name: "",
      approved_amount: "5000.00",
    });
    expect(result.success).toBe(false);
  });

  it("rejects invalid amount", () => {
    const result = budgetLineFormSchema.safeParse({
      name: "Personal",
      approved_amount: "invalid",
    });
    expect(result.success).toBe(false);
  });
});

describe("fundingSourceFormSchema", () => {
  it("validates a valid funding source form", () => {
    const result = fundingSourceFormSchema.safeParse({
      name: "MinCiencias",
      amount: "8000.00",
    });
    expect(result.success).toBe(true);
  });

  it("rejects empty name", () => {
    const result = fundingSourceFormSchema.safeParse({
      name: "",
      amount: "8000.00",
    });
    expect(result.success).toBe(false);
  });
});

describe("budgetExecutionFormSchema", () => {
  it("validates a valid execution form", () => {
    const result = budgetExecutionFormSchema.safeParse({
      amount: "1000.00",
      executed_at: "2026-03-15",
    });
    expect(result.success).toBe(true);
  });

  it("rejects missing executed_at", () => {
    const result = budgetExecutionFormSchema.safeParse({
      amount: "1000.00",
      executed_at: "",
    });
    expect(result.success).toBe(false);
  });

  it("accepts optional authorization fields", () => {
    const result = budgetExecutionFormSchema.safeParse({
      amount: "1000.00",
      executed_at: "2026-03-15",
      authorized_by: "user-1",
      authorized_at: "2026-03-15T10:00:00Z",
    });
    expect(result.success).toBe(true);
  });
});

describe("budgetAttachmentFormSchema", () => {
  it("validates a valid attachment form", () => {
    const result = budgetAttachmentFormSchema.safeParse({
      name: "Formulación",
      doc_type: "formulacion",
      external_url: "https://example.com/doc.pdf",
    });
    expect(result.success).toBe(true);
  });

  it("rejects invalid URL", () => {
    const result = budgetAttachmentFormSchema.safeParse({
      name: "Formulación",
      doc_type: "formulacion",
      external_url: "not-a-url",
    });
    expect(result.success).toBe(false);
  });

  it("rejects invalid doc_type", () => {
    const result = budgetAttachmentFormSchema.safeParse({
      name: "Formulación",
      doc_type: "invalid_type",
      external_url: "https://example.com/doc.pdf",
    });
    expect(result.success).toBe(false);
  });
});

describe("buildCreateBudgetPayload", () => {
  it("builds payload from form values", () => {
    const values = {
      project: "project-1",
      name: "Presupuesto 2026",
      approved_amount: "10000.00",
    };
    const payload = buildCreateBudgetPayload(values);
    expect(payload).toEqual(values);
  });
});

describe("buildCreateBudgetLinePayload", () => {
  it("builds payload from form values", () => {
    const values = {
      name: "Personal",
      approved_amount: "5000.00",
    };
    const payload = buildCreateBudgetLinePayload(values);
    expect(payload).toEqual(values);
  });
});
