/**
 * Calls form schema — conditional entity and date ordering rules.
 *
 * Spec (calls-ui create):
 *   - external_entity required for external calls, forbidden for internal.
 *   - when present, end dates must be on or after start dates.
 *   - successful internal submits omit external_entity from the payload.
 */

import {
  buildCallPayload,
  callFormSchema,
  type CallFormValues,
} from "@/features/calls/schemas";

const validInternal: CallFormValues = {
  title: "Convocatoria interna",
  description: "Investigación interna.",
  call_type: "internal",
  external_entity: "",
  submission_start: "2026-02-01",
  submission_end: "2026-03-01",
  evaluation_start: undefined,
  evaluation_end: undefined,
};

function issuesFor(input: CallFormValues, path: string): string[] {
  const result = callFormSchema.safeParse(input);
  if (result.success) return [];
  return result.error.issues
    .filter((i) => i.path.join(".") === path)
    .map((i) => i.message);
}

describe("callFormSchema — internal calls", () => {
  it("accepts a valid internal call without external_entity", () => {
    const result = callFormSchema.safeParse(validInternal);
    expect(result.success).toBe(true);
  });

  it("rejects an internal call that carries an external entity", () => {
    const messages = issuesFor(
      { ...validInternal, external_entity: "Ministerio" },
      "external_entity",
    );
    expect(messages).toHaveLength(1);
    expect(messages[0]).toMatch(/internas no pueden tener/i);
  });
});

describe("callFormSchema — external calls", () => {
  it("rejects an external call without an entity", () => {
    const messages = issuesFor(
      { ...validInternal, call_type: "external" },
      "external_entity",
    );
    expect(messages).toHaveLength(1);
    expect(messages[0]).toMatch(/entidad externa es obligatoria/i);
  });

  it("accepts an external call with an entity", () => {
    const result = callFormSchema.safeParse({
      ...validInternal,
      call_type: "external",
      external_entity: "Ministerio de Ciencia",
    });
    expect(result.success).toBe(true);
  });
});

describe("callFormSchema — date ordering", () => {
  it("rejects submission_end before submission_start", () => {
    const messages = issuesFor(
      {
        ...validInternal,
        submission_start: "2026-03-01",
        submission_end: "2026-02-01",
      },
      "submission_end",
    );
    expect(messages).toHaveLength(1);
    expect(messages[0]).toMatch(/posterior o igual/i);
  });

  it("rejects evaluation_end before evaluation_start", () => {
    const messages = issuesFor(
      {
        ...validInternal,
        evaluation_start: "2026-04-01",
        evaluation_end: "2026-03-01",
      },
      "evaluation_end",
    );
    expect(messages).toHaveLength(1);
  });

  it("accepts end dates equal to start dates", () => {
    const result = callFormSchema.safeParse({
      ...validInternal,
      submission_start: "2026-02-01",
      submission_end: "2026-02-01",
      evaluation_start: "2026-03-01",
      evaluation_end: "2026-03-01",
    });
    expect(result.success).toBe(true);
  });
});

describe("buildCallPayload — writable field projection", () => {
  it("omits external_entity for internal calls", () => {
    const payload = buildCallPayload(validInternal);
    expect("external_entity" in payload).toBe(false);
    expect(payload.call_type).toBe("internal");
    expect(payload.submission_start).toBe("2026-02-01");
  });

  it("includes external_entity for external calls", () => {
    const payload = buildCallPayload({
      ...validInternal,
      call_type: "external",
      external_entity: "Ministerio de Ciencia",
    });
    expect(payload.external_entity).toBe("Ministerio de Ciencia");
  });

  it("omits empty dates and leaves read-only fields out", () => {
    const payload = buildCallPayload({
      ...validInternal,
      submission_start: "",
      submission_end: "",
    });
    expect("submission_start" in payload).toBe(false);
    expect("submission_end" in payload).toBe(false);
    expect("status" in payload).toBe(false);
    expect("institution" in payload).toBe(false);
  });
});