/**
 * Researchers Zod schemas — create/edit form validation.
 *
 * Spec (researchers-ui create/edit): the researcher create form validates
 * against ResearcherCreateSerializer writable fields; required fields
 * surface Spanish messages; optional text fields normalize to "".
 */

import { researcherCreateSchema, researcherEditSchema } from "@/features/researchers/schemas";

describe("researcherCreateSchema", () => {
  it("accepts a valid researcher payload", () => {
    const result = researcherCreateSchema.safeParse({
      first_name: "Ana",
      last_name: "Pérez",
      document_type: "CC",
      document_number: "1234567890",
      primary_email: "ana.perez@example.com",
      phone: "+57 300 1234567",
      bio: "Investigadora principal.",
      academic_formation: "Doctorado en Ciencias",
      is_active: true,
    });
    expect(result.success).toBe(true);
  });

  it("rejects a missing first name with a Spanish message", () => {
    const result = researcherCreateSchema.safeParse({
      first_name: "",
      last_name: "Pérez",
      document_type: "CC",
      document_number: "123",
      primary_email: "a@example.com",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.message).toMatch(/obligatorio/i);
      expect(result.error.issues[0]?.path).toContain("first_name");
    }
  });

  it("rejects an invalid primary email", () => {
    const result = researcherCreateSchema.safeParse({
      first_name: "Ana",
      last_name: "Pérez",
      document_type: "CC",
      document_number: "123",
      primary_email: "not-an-email",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.path).toContain("primary_email");
    }
  });

  it("normalizes optional text fields to empty strings", () => {
    const result = researcherCreateSchema.safeParse({
      first_name: "Ana",
      last_name: "Pérez",
      document_type: "CC",
      document_number: "123",
      primary_email: "ana@example.com",
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.phone).toBe("");
      expect(result.data.bio).toBe("");
      expect(result.data.academic_formation).toBe("");
    }
  });
});

describe("researcherEditSchema", () => {
  it("accepts a valid edit payload with is_active", () => {
    const result = researcherEditSchema.safeParse({
      first_name: "Ana",
      last_name: "Pérez",
      document_type: "CC",
      document_number: "1234567890",
      primary_email: "ana.perez@example.com",
      phone: "+57 300 1234567",
      bio: "Bio.",
      academic_formation: "Doctorado",
      is_active: true,
    });
    expect(result.success).toBe(true);
  });

  it("rejects an edit without a document number", () => {
    const result = researcherEditSchema.safeParse({
      first_name: "Ana",
      last_name: "Pérez",
      document_type: "CC",
      document_number: "",
      primary_email: "ana@example.com",
      is_active: false,
    });
    expect(result.success).toBe(false);
  });
});
