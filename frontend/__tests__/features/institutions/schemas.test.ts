/**
 * Institutions Zod schemas — per-entity validation.
 *
 * Spec (institutions-ui RF-F02): RHF + zod validates the institution
 * create/edit form; invalid payloads surface Spanish field messages.
 */

import {
  institutionSchema,
  sedeSchema,
  facultadSchema,
  centerSchema,
  groupSchema,
  lineSchema,
} from "@/features/institutions/schemas";

describe("institutionSchema", () => {
  it("accepts a valid institution payload", () => {
    const result = institutionSchema.safeParse({
      name: "Universidad Nacional",
      code: "UNAL",
      description: "Institución pública",
      address: "Av. Principal 123",
      contact_email: "contacto@unal.edu",
      contact_phone: "+57 1 1234567",
      logo_url: "https://example.com/logo.png",
    });
    expect(result.success).toBe(true);
  });

  it("rejects a missing name with a Spanish message", () => {
    const result = institutionSchema.safeParse({
      name: "",
      code: "UNAL",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.message).toMatch(/obligatorio/i);
      expect(result.error.issues[0]?.path).toContain("name");
    }
  });

  it("rejects an invalid contact email", () => {
    const result = institutionSchema.safeParse({
      name: "Universidad",
      code: "U1",
      contact_email: "not-an-email",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.path).toContain("contact_email");
    }
  });

  it("normalizes optional fields to empty strings", () => {
    const result = institutionSchema.safeParse({
      name: "Universidad",
      code: "U1",
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.description).toBe("");
      expect(result.data.address).toBe("");
      expect(result.data.contact_email).toBe("");
    }
  });
});

describe("sedeSchema", () => {
  it("accepts a valid sede payload", () => {
    const result = sedeSchema.safeParse({
      code: "S1",
      name: "Sede Bogotá",
      description: "Campus principal",
    });
    expect(result.success).toBe(true);
  });

  it("rejects a sede without name", () => {
    const result = sedeSchema.safeParse({ code: "S1", name: "" });
    expect(result.success).toBe(false);
  });
});

describe("facultadSchema", () => {
  it("accepts a facultad without a sede (optional parent)", () => {
    const result = facultadSchema.safeParse({
      code: "F1",
      name: "Facultad de Ingeniería",
      description: "",
    });
    expect(result.success).toBe(true);
  });

  it("accepts a facultad with a sede id", () => {
    const result = facultadSchema.safeParse({
      sede: "sede-1",
      code: "F1",
      name: "Facultad de Ingeniería",
    });
    expect(result.success).toBe(true);
  });
});

describe("centerSchema", () => {
  it("accepts a center with optional sede/facultad and contact fields", () => {
    const result = centerSchema.safeParse({
      code: "C1",
      name: "Centro de Inteligencia Artificial",
      description: "",
      sede: "sede-1",
      facultad: "fac-1",
      contact_email: "ia@unal.edu",
      contact_phone: "+57 1 9999999",
    });
    expect(result.success).toBe(true);
  });

  it("rejects a center with a malformed contact email", () => {
    const result = centerSchema.safeParse({
      code: "C1",
      name: "Centro IA",
      contact_email: "bad",
    });
    expect(result.success).toBe(false);
  });
});

describe("groupSchema / lineSchema", () => {
  it("accepts a valid group payload", () => {
    expect(
      groupSchema.safeParse({ code: "G1", name: "Grupo de IA", description: "" }).success,
    ).toBe(true);
  });

  it("accepts a valid line payload", () => {
    expect(lineSchema.safeParse({ code: "L1", name: "Línea de ML", description: "" }).success).toBe(
      true,
    );
  });

  it("rejects a group without code", () => {
    const result = groupSchema.safeParse({ code: "", name: "Grupo" });
    expect(result.success).toBe(false);
  });
});
